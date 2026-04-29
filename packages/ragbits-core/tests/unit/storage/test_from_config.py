"""Smoke test for ``DatabaseConnection.subclass_from_config``."""

from __future__ import annotations

import pytest

from ragbits.core.storage.connections import DatabaseConnection, SQLiteConnection
from ragbits.core.utils.config_handling import ObjectConstructionConfig


@pytest.mark.asyncio
async def test_sqlite_connection_from_config() -> None:
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.storage.connections:SQLiteConnection",
            "config": {"db_path": ":memory:"},
        }
    )
    conn: DatabaseConnection = DatabaseConnection.subclass_from_config(config)
    try:
        assert isinstance(conn, SQLiteConnection)
        assert conn.placeholder_style == "qmark"
        async with conn:
            await conn.execute("CREATE TABLE t (id INTEGER)")
            assert await conn.fetch_val("SELECT COUNT(*) FROM t") == 0
    finally:
        await conn.disconnect()
