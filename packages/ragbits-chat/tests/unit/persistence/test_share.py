"""Unit tests for :class:`SQLSharePersistence` against a real SQLite backend."""

from collections.abc import AsyncIterator

import pytest

from ragbits.chat.persistence.share import (
    SharePersistence,
    SQLSharePersistence,
    SQLSharePersistenceOptions,
)
from ragbits.core.storage.connections import SQLiteConnection


@pytest.fixture
async def share_persistence() -> AsyncIterator[SQLSharePersistence]:
    """Build an in-memory SQLite-backed share persistence for tests."""
    connection = SQLiteConnection(db_path=":memory:")
    try:
        yield SQLSharePersistence(connection)
    finally:
        await connection.disconnect()


def test_backwards_compatible_alias() -> None:
    """``SharePersistence`` must keep pointing at ``SQLSharePersistence``."""
    assert SharePersistence is SQLSharePersistence


@pytest.mark.asyncio
async def test_table_name_from_options() -> None:
    """Custom ``shares_table`` from options is used for DDL."""
    connection = SQLiteConnection(db_path=":memory:")
    try:
        options = SQLSharePersistenceOptions(shares_table="custom_shares")
        store = SQLSharePersistence(connection, options)
        await store.set_shares("conv-1", "alice", ["bob"])

        rows = await connection.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            "custom_shares",
        )
        assert [r["name"] for r in rows] == ["custom_shares"]
    finally:
        await connection.disconnect()


@pytest.mark.asyncio
async def test_set_shares_inserts_new_recipients(share_persistence: SQLSharePersistence) -> None:
    result = await share_persistence.set_shares("conv-1", "alice", ["bob"])

    assert len(result) == 1
    assert result[0]["recipient"] == "bob"
    assert result[0]["owner_id"] == "alice"
    assert result[0]["hidden"] is False
    assert result[0]["conversation_id"] == "conv-1"


@pytest.mark.asyncio
async def test_set_shares_unhides_existing(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])
    assert await share_persistence.hide_share("conv-1", ["bob"]) is True

    result = await share_persistence.set_shares("conv-1", "alice", ["bob"])

    assert len(result) == 1
    assert result[0]["hidden"] is False
    assert await share_persistence.can_access("conv-1", ["bob"]) is True


@pytest.mark.asyncio
async def test_set_shares_idempotent_for_same_owner(share_persistence: SQLSharePersistence) -> None:
    """Running ``set_shares`` twice for the same owner converges (no duplicates)."""
    first = await share_persistence.set_shares("conv-1", "alice", ["bob"])
    second = await share_persistence.set_shares("conv-1", "alice", ["bob"])

    assert len(first) == 1
    assert len(second) == 1
    assert first[0]["id"] == second[0]["id"], "UPSERT should keep the same row id"

    shares = await share_persistence.get_shares("conv-1", "alice")
    assert len(shares) == 1


@pytest.mark.asyncio
async def test_set_shares_empty_recipients(share_persistence: SQLSharePersistence) -> None:
    result = await share_persistence.set_shares("conv-1", "alice", [])

    assert result == []


@pytest.mark.asyncio
async def test_get_shares_returns_only_owner_rows(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob", "charlie"])
    await share_persistence.set_shares("conv-2", "eve", ["bob"])

    result = await share_persistence.get_shares("conv-1", "alice")

    recipients = {row["recipient"] for row in result}
    assert recipients == {"bob", "charlie"}


@pytest.mark.asyncio
async def test_get_shares_skips_hidden(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob", "charlie"])
    await share_persistence.hide_share("conv-1", ["bob"])

    result = await share_persistence.get_shares("conv-1", "alice")

    assert [row["recipient"] for row in result] == ["charlie"]


@pytest.mark.asyncio
async def test_remove_shares(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob", "charlie"])

    await share_persistence.remove_shares("conv-1", "alice", ["bob"])

    remaining = await share_persistence.get_shares("conv-1", "alice")
    assert [row["recipient"] for row in remaining] == ["charlie"]


@pytest.mark.asyncio
async def test_remove_shares_empty_noop(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])

    await share_persistence.remove_shares("conv-1", "alice", [])

    assert len(await share_persistence.get_shares("conv-1", "alice")) == 1


@pytest.mark.asyncio
async def test_remove_shares_only_affects_matching_owner(share_persistence: SQLSharePersistence) -> None:
    """``remove_shares`` only deletes rows owned by the given owner."""
    await share_persistence.set_shares("conv-1", "alice", ["bob"])
    await share_persistence.set_shares("conv-2", "eve", ["bob"])

    await share_persistence.remove_shares("conv-1", "carol", ["bob"])

    assert await share_persistence.can_access("conv-1", ["bob"]) is True
    assert await share_persistence.can_access("conv-2", ["bob"]) is True


@pytest.mark.asyncio
async def test_list_shared_with_me(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])
    await share_persistence.set_shares("conv-2", "eve", ["charlie"])

    result = await share_persistence.list_shared_with_me(["bob"])

    assert len(result) == 1
    assert result[0]["conversation_id"] == "conv-1"


@pytest.mark.asyncio
async def test_list_shared_with_me_accepts_multiple_identifiers(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])
    await share_persistence.set_shares("conv-2", "alice", ["bob@example.com"])

    result = await share_persistence.list_shared_with_me(["bob", "bob@example.com"])

    assert {row["conversation_id"] for row in result} == {"conv-1", "conv-2"}


@pytest.mark.asyncio
async def test_list_shared_with_me_paginates(share_persistence: SQLSharePersistence) -> None:
    """``limit``/``offset`` slices the result set, newest first."""
    for i in range(5):
        await share_persistence.set_shares(f"conv-{i}", "alice", ["bob"])

    page = await share_persistence.list_shared_with_me(["bob"], limit=2, offset=0)
    next_page = await share_persistence.list_shared_with_me(["bob"], limit=2, offset=2)

    assert len(page) == 2
    assert len(next_page) == 2
    page_ids = {r["conversation_id"] for r in page}
    next_ids = {r["conversation_id"] for r in next_page}
    assert page_ids.isdisjoint(next_ids)


@pytest.mark.asyncio
async def test_list_shared_with_me_empty_user(share_persistence: SQLSharePersistence) -> None:
    assert await share_persistence.list_shared_with_me([]) == []


@pytest.mark.asyncio
async def test_can_access_true(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])

    assert await share_persistence.can_access("conv-1", ["bob"]) is True


@pytest.mark.asyncio
async def test_can_access_with_multiple_identifiers(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob@example.com"])

    assert await share_persistence.can_access("conv-1", ["bob", "bob@example.com"]) is True


@pytest.mark.asyncio
async def test_can_access_false(share_persistence: SQLSharePersistence) -> None:
    assert await share_persistence.can_access("conv-1", ["bob"]) is False


@pytest.mark.asyncio
async def test_can_access_hidden_returns_false(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])
    await share_persistence.hide_share("conv-1", ["bob"])

    assert await share_persistence.can_access("conv-1", ["bob"]) is False


@pytest.mark.asyncio
async def test_can_access_empty_user(share_persistence: SQLSharePersistence) -> None:
    assert await share_persistence.can_access("conv-1", []) is False


@pytest.mark.asyncio
async def test_hide_share_success(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob"])

    assert await share_persistence.hide_share("conv-1", ["bob"]) is True
    assert await share_persistence.can_access("conv-1", ["bob"]) is False


@pytest.mark.asyncio
async def test_hide_share_with_multiple_identifiers(share_persistence: SQLSharePersistence) -> None:
    await share_persistence.set_shares("conv-1", "alice", ["bob@example.com"])

    assert await share_persistence.hide_share("conv-1", ["bob", "bob@example.com"]) is True
    assert await share_persistence.can_access("conv-1", ["bob", "bob@example.com"]) is False


@pytest.mark.asyncio
async def test_hide_share_not_found(share_persistence: SQLSharePersistence) -> None:
    assert await share_persistence.hide_share("conv-1", ["bob"]) is False


@pytest.mark.asyncio
async def test_hide_share_already_hidden_returns_false(share_persistence: SQLSharePersistence) -> None:
    """A second hide is a no-op (no visible row matches)."""
    await share_persistence.set_shares("conv-1", "alice", ["bob"])
    await share_persistence.hide_share("conv-1", ["bob"])

    assert await share_persistence.hide_share("conv-1", ["bob"]) is False


@pytest.mark.asyncio
async def test_mixed_case_identifiers_normalised_end_to_end(share_persistence: SQLSharePersistence) -> None:
    """Owner and recipient identifiers must be compared case-insensitively.

    A user identified as ``Alice`` by the auth backend should still be able to
    share with ``BOB@Example.com`` and have ``bob`` look up the conversation.
    """
    await share_persistence.set_shares("conv-1", "Alice", ["BOB@Example.com"])

    assert await share_persistence.can_access("conv-1", ["bob@example.com"]) is True
    shares = await share_persistence.get_shares("conv-1", "alice")
    assert [row["recipient"] for row in shares] == ["bob@example.com"]
    assert [row["owner_id"] for row in shares] == ["alice"]

    assert await share_persistence.hide_share("conv-1", ["BOB@Example.com"]) is True
    assert await share_persistence.can_access("conv-1", ["bob@example.com"]) is False


@pytest.mark.asyncio
async def test_set_shares_deduplicates_case_variants(share_persistence: SQLSharePersistence) -> None:
    result = await share_persistence.set_shares("conv-1", "alice", ["bob", "BOB", "Bob"])

    assert len(result) == 1
    shares = await share_persistence.get_shares("conv-1", "alice")
    assert [row["recipient"] for row in shares] == ["bob"]


@pytest.mark.asyncio
async def test_unsupported_connection_raises_type_error() -> None:
    """SharePersistence should refuse to silently work with unknown connections."""

    class _Stub:
        pass

    with pytest.raises(TypeError):
        SQLSharePersistence(_Stub())  # type: ignore[arg-type]
