"""Key-value store abstractions.

This module provides pluggable key-value store implementations for
simple key-value persistence with optional TTL support.

Example:
    ```python
    from ragbits.core.storage.connections import PostgresConnection
    from ragbits.core.storage.kv_store import PostgresKVStore

    conn = PostgresConnection(host="localhost", database="mydb")
    store = PostgresKVStore(connection=conn, table_name="app_cache")

    async with store:
        await store.set("config", {"debug": True}, ttl_seconds=3600)
        config = await store.get("config")
    ```
"""

from ragbits.core.storage.kv_store.base import KVStore

__all__ = ["KVStore"]

# PostgreSQL store is optional (requires asyncpg)
try:
    from ragbits.core.storage.kv_store.postgres import PostgresKVStore  # noqa: F401

    __all__.append("PostgresKVStore")
except ImportError:
    pass

# SQLite store is optional (requires aiosqlite)
try:
    from ragbits.core.storage.kv_store.sqlite import SQLiteKVStore  # noqa: F401

    __all__.append("SQLiteKVStore")
except ImportError:
    pass
