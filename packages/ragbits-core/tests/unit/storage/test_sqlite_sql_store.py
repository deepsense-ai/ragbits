"""Tests for :class:`SQLiteSQLStore` against an in-memory SQLite backend.

Covers the previously broken ``execute_returning`` (used to ``SELECT * FROM
sqlite_master``) and verifies that ``__aexit__`` no longer closes the
caller-owned connection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from ragbits.core.storage.connections import SQLiteConnection
from ragbits.core.storage.sql_store import SQLiteSQLStore


class _ItemsStore(SQLiteSQLStore):
    """Concrete subclass exposing a tiny ``items`` schema for tests."""

    async def _create_schema(self) -> None:
        await self._connection.execute(
            f"CREATE TABLE IF NOT EXISTS {self._prefixed_table('items')} ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT NOT NULL, "
            "qty INTEGER NOT NULL"
            ")"
        )


@pytest.fixture
async def store() -> AsyncIterator[_ItemsStore]:
    connection = SQLiteConnection(db_path=":memory:")
    try:
        store = _ItemsStore(connection, table_prefix="t_")
        async with store:
            yield store
    finally:
        await connection.disconnect()


@pytest.mark.asyncio
async def test_table_prefix_applied(store: _ItemsStore) -> None:
    rows = await store._connection.fetch_all(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        "t_items",
    )
    assert [r["name"] for r in rows] == ["t_items"]


@pytest.mark.asyncio
async def test_execute_and_fetch(store: _ItemsStore) -> None:
    rowcount = await store.execute("INSERT INTO t_items (name, qty) VALUES (?, ?)", "a", 1)
    assert rowcount == 1

    row = await store.fetch_one("SELECT name, qty FROM t_items WHERE name = ?", "a")
    assert row == {"name": "a", "qty": 1}

    rows = await store.fetch_all("SELECT name FROM t_items ORDER BY name")
    assert [r["name"] for r in rows] == ["a"]


@pytest.mark.asyncio
async def test_execute_returning_returns_inserted_row(store: _ItemsStore) -> None:
    """SQLite ≥ 3.35 supports ``RETURNING``; the store must surface it."""
    row = await store.execute_returning(
        "INSERT INTO t_items (name, qty) VALUES (?, ?) RETURNING id, name, qty",
        "alpha",
        7,
    )
    assert row is not None
    assert row["name"] == "alpha"
    assert row["qty"] == 7
    assert isinstance(row["id"], int)


@pytest.mark.asyncio
async def test_fetch_val_falls_back_when_connection_lacks_method(store: _ItemsStore) -> None:
    """Plain SQL stores expose ``fetch_val`` even when the underlying connection lacks it."""
    await store.execute("INSERT INTO t_items (name, qty) VALUES (?, ?)", "b", 5)

    val = await store.fetch_val("SELECT qty FROM t_items WHERE name = ?", "b")
    assert val == 5


@pytest.mark.asyncio
async def test_aexit_does_not_disconnect_caller_connection() -> None:
    """Stores must not own connection lifecycle."""
    connection = SQLiteConnection(db_path=":memory:")
    try:
        store_a = _ItemsStore(connection, table_prefix="a_")
        store_b = _ItemsStore(connection, table_prefix="b_")

        async with store_a:
            await store_a.execute("INSERT INTO a_items (name, qty) VALUES (?, ?)", "x", 1)

        # Connection must still be alive and usable.
        async with store_b:
            row = await store_a.fetch_one("SELECT qty FROM a_items WHERE name = ?", "x")
            assert row == {"qty": 1}
            await store_b.execute("INSERT INTO b_items (name, qty) VALUES (?, ?)", "y", 2)
            row = await store_b.fetch_one("SELECT qty FROM b_items WHERE name = ?", "y")
            assert row == {"qty": 2}
    finally:
        await connection.disconnect()
