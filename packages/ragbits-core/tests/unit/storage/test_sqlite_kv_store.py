"""Tests for :class:`SQLiteKVStore` against an in-memory SQLite backend.

These fixtures pin down the bug fixes around:

- ``delete()`` correctly returning ``True``/``False`` (regression for the
  Postgres ``"DELETE 1" in str(result)`` substring bug, mirrored here for
  feature parity).
- ``__aexit__`` not closing the caller-owned connection so the same
  ``SQLiteConnection`` can be reused across multiple stores.
- TTL-based expiry being honoured by ``get`` / ``exists`` / ``cleanup_expired``.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import pytest

from ragbits.core.storage.connections import SQLiteConnection
from ragbits.core.storage.kv_store import SQLiteKVStore


@pytest.fixture
async def kv_store() -> AsyncIterator[SQLiteKVStore]:
    connection = SQLiteConnection(db_path=":memory:")
    try:
        store = SQLiteKVStore(connection, table_name="kv_items")
        async with store:
            yield store
    finally:
        await connection.disconnect()


@pytest.mark.asyncio
async def test_set_and_get_roundtrip(kv_store: SQLiteKVStore) -> None:
    await kv_store.set("user:1", {"name": "alice", "age": 30})

    value = await kv_store.get("user:1")
    assert value == {"name": "alice", "age": 30}


@pytest.mark.asyncio
async def test_get_missing_returns_none(kv_store: SQLiteKVStore) -> None:
    assert await kv_store.get("missing") is None


@pytest.mark.asyncio
async def test_set_overwrites_existing(kv_store: SQLiteKVStore) -> None:
    await kv_store.set("k", {"v": 1})
    await kv_store.set("k", {"v": 2})

    assert await kv_store.get("k") == {"v": 2}


@pytest.mark.asyncio
async def test_delete_existing_returns_true(kv_store: SQLiteKVStore) -> None:
    await kv_store.set("k", {"v": 1})

    assert await kv_store.delete("k") is True
    assert await kv_store.get("k") is None


@pytest.mark.asyncio
async def test_delete_missing_returns_false(kv_store: SQLiteKVStore) -> None:
    assert await kv_store.delete("never-set") is False


@pytest.mark.asyncio
async def test_exists(kv_store: SQLiteKVStore) -> None:
    assert await kv_store.exists("k") is False
    await kv_store.set("k", {"v": 1})
    assert await kv_store.exists("k") is True


@pytest.mark.asyncio
async def test_keys_glob(kv_store: SQLiteKVStore) -> None:
    await kv_store.set("user:1", {"name": "a"})
    await kv_store.set("user:2", {"name": "b"})
    await kv_store.set("post:1", {"title": "x"})

    user_keys = await kv_store.keys("user:*")
    assert sorted(user_keys) == ["user:1", "user:2"]

    all_keys = await kv_store.keys("*")
    assert sorted(all_keys) == ["post:1", "user:1", "user:2"]


@pytest.mark.asyncio
async def test_ttl_expires_value(kv_store: SQLiteKVStore) -> None:
    """Setting a past ``expires_at`` lets us prove TTL filtering without ``sleep``."""
    insert_sql = f"INSERT INTO {kv_store._table_name} (key, value, expires_at) VALUES (?, ?, ?)"  # noqa: S608
    await kv_store._connection.execute(insert_sql, "expired", '{"v": 1}', time.time() - 1)

    assert await kv_store.get("expired") is None
    assert await kv_store.exists("expired") is False


@pytest.mark.asyncio
async def test_cleanup_expired_returns_count(kv_store: SQLiteKVStore) -> None:
    now = time.time()
    insert_sql = f"INSERT INTO {kv_store._table_name} (key, value, expires_at) VALUES (?, ?, ?)"  # noqa: S608
    await kv_store._connection.execute(insert_sql, "stale", '{"v": 1}', now - 10)
    await kv_store._connection.execute(insert_sql, "live", '{"v": 2}', now + 60)

    removed = await kv_store.cleanup_expired()

    assert removed == 1
    assert await kv_store.exists("live") is True


@pytest.mark.asyncio
async def test_get_many_and_set_many(kv_store: SQLiteKVStore) -> None:
    await kv_store.set_many({"a": {"v": 1}, "b": {"v": 2}})

    result = await kv_store.get_many(["a", "b", "c"])
    assert result == {"a": {"v": 1}, "b": {"v": 2}, "c": None}


@pytest.mark.asyncio
async def test_aexit_does_not_disconnect_caller_connection() -> None:
    """Stores must not own connection lifecycle: a shared connection survives ``__aexit__``."""
    connection = SQLiteConnection(db_path=":memory:")
    try:
        store_a = SQLiteKVStore(connection, table_name="kv_a")
        store_b = SQLiteKVStore(connection, table_name="kv_b")

        async with store_a:
            await store_a.set("k", {"from": "a"})
        # Connection must still be live and usable through store_b.
        async with store_b:
            await store_b.set("k", {"from": "b"})
            assert await store_b.get("k") == {"from": "b"}
        # And store_a's data is still there too.
        async with store_a:
            assert await store_a.get("k") == {"from": "a"}
    finally:
        await connection.disconnect()
