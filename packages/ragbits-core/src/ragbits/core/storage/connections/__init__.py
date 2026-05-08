"""Database connection abstractions.

This module provides pluggable database connection implementations
with connection pooling, async support, and lazy initialization.

Example:
    ```python
    from ragbits.core.storage.connections import PostgresConnection, SQLiteConnection

    # PostgreSQL with connection pooling
    pg_conn = PostgresConnection(
        host="localhost",
        database="mydb",
        user="postgres",
        password="secret",
    )

    # SQLite (file or in-memory)
    sqlite_conn = SQLiteConnection(db_path="./data.db")

    # Use as async context manager
    async with pg_conn:
        row = await pg_conn.fetch_one("SELECT * FROM users WHERE id = $1", 1)
    ```
"""

from ragbits.core.storage.connections.base import DatabaseConnection

__all__ = ["DatabaseConnection"]

# PostgreSQL connection is optional (requires asyncpg)
try:
    from ragbits.core.storage.connections.postgres import PostgresConnection  # noqa: F401

    __all__.append("PostgresConnection")
except ImportError:
    pass

# SQLite connection is optional (requires aiosqlite)
try:
    from ragbits.core.storage.connections.sqlite import SQLiteConnection  # noqa: F401

    __all__.append("SQLiteConnection")
except ImportError:
    pass
