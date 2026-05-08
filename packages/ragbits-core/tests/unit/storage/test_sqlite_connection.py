"""Tests for :class:`SQLiteConnection`.

Run against an in-memory SQLite database so the suite stays self-contained.
The fixtures cover the abstract :class:`DatabaseConnection` contract — these
also exercise the bug fixes around ``execute()`` returning rowcount and the
transaction context manager respecting commit/rollback semantics.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from ragbits.core.storage.connections import SQLiteConnection


@pytest.fixture
async def connection() -> AsyncIterator[SQLiteConnection]:
    conn = SQLiteConnection(db_path=":memory:")
    try:
        async with conn:
            await conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, qty INTEGER NOT NULL)")
            yield conn
    finally:
        await conn.disconnect()


@pytest.mark.asyncio
async def test_placeholder_style() -> None:
    assert SQLiteConnection.placeholder_style == "qmark"
    assert SQLiteConnection().placeholder(1) == "?"
    assert SQLiteConnection().placeholder(7) == "?"


@pytest.mark.asyncio
async def test_execute_returns_rowcount(connection: SQLiteConnection) -> None:
    rowcount = await connection.execute("INSERT INTO items (name, qty) VALUES (?, ?)", "apple", 3)
    assert rowcount == 1

    rowcount = await connection.execute("UPDATE items SET qty = qty + 1")
    assert rowcount == 1

    rowcount = await connection.execute("DELETE FROM items WHERE name = ?", "missing")
    assert rowcount == 0


@pytest.mark.asyncio
async def test_execute_ddl_returns_zero(connection: SQLiteConnection) -> None:
    rowcount = await connection.execute("CREATE TABLE tmp (x INTEGER)")
    assert rowcount == 0


@pytest.mark.asyncio
async def test_fetch_one_and_all(connection: SQLiteConnection) -> None:
    await connection.execute_many(
        "INSERT INTO items (name, qty) VALUES (?, ?)",
        [("a", 1), ("b", 2), ("c", 3)],
    )

    one = await connection.fetch_one("SELECT name, qty FROM items WHERE name = ?", "b")
    assert one == {"name": "b", "qty": 2}

    rows = await connection.fetch_all("SELECT name FROM items ORDER BY name")
    assert [r["name"] for r in rows] == ["a", "b", "c"]

    val = await connection.fetch_val("SELECT COUNT(*) FROM items")
    assert val == 3

    missing = await connection.fetch_one("SELECT name FROM items WHERE name = ?", "zzz")
    assert missing is None


@pytest.mark.asyncio
async def test_transaction_commits(connection: SQLiteConnection) -> None:
    async with connection.transaction():
        await connection.execute("INSERT INTO items (name, qty) VALUES (?, ?)", "a", 1)
        await connection.execute("INSERT INTO items (name, qty) VALUES (?, ?)", "b", 2)

    count = await connection.fetch_val("SELECT COUNT(*) FROM items")
    assert count == 2


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_exception(connection: SQLiteConnection) -> None:
    async def insert_then_fail() -> None:
        async with connection.transaction():
            await connection.execute("INSERT INTO items (name, qty) VALUES (?, ?)", "a", 1)
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await insert_then_fail()

    count = await connection.fetch_val("SELECT COUNT(*) FROM items")
    assert count == 0


@pytest.mark.asyncio
async def test_transaction_does_not_nest(connection: SQLiteConnection) -> None:
    async with connection.transaction():
        with pytest.raises(RuntimeError, match="does not support nesting"):
            async with connection.transaction():
                pass


@pytest.mark.asyncio
async def test_concurrent_transactions_are_serialized(connection: SQLiteConnection) -> None:
    """Two awaiting tasks must converge on a consistent final state."""

    async def insert(name: str) -> None:
        async with connection.transaction():
            await connection.execute("INSERT INTO items (name, qty) VALUES (?, ?)", name, 1)

    await asyncio.gather(insert("a"), insert("b"), insert("c"))

    rows = await connection.fetch_all("SELECT name FROM items ORDER BY name")
    assert [r["name"] for r in rows] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_aexit_disconnects() -> None:
    conn = SQLiteConnection(db_path=":memory:")
    async with conn:
        await conn.execute("CREATE TABLE t (id INTEGER)")
        assert conn._initialized is True
    assert conn._connection is None
    assert conn._initialized is False
