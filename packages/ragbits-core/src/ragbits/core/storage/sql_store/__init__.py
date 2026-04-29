"""SQL store abstractions.

This module provides pluggable SQL store implementations for structured
data persistence with automatic schema management.

Example:
    ```python
    from ragbits.core.storage.connections import PostgresConnection
    from ragbits.core.storage.sql_store import PostgresSQLStore

    conn = PostgresConnection(host="localhost", database="mydb")
    store = PostgresSQLStore(connection=conn, table_prefix="app_")

    async with store:
        await store.execute("INSERT INTO app_users (name) VALUES ($1)", "Alice")
        users = await store.fetch_all("SELECT * FROM app_users")
    ```
"""

from ragbits.core.storage.sql_store.base import SQLStore

__all__ = ["SQLStore"]

# PostgreSQL store is optional (requires asyncpg)
try:
    from ragbits.core.storage.sql_store.postgres import PostgresSQLStore  # noqa: F401

    __all__.append("PostgresSQLStore")
except ImportError:
    pass

# SQLite store is optional (requires aiosqlite)
try:
    from ragbits.core.storage.sql_store.sqlite import SQLiteSQLStore  # noqa: F401

    __all__.append("SQLiteSQLStore")
except ImportError:
    pass
