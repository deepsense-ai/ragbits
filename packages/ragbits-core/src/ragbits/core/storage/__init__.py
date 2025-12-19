"""Storage abstractions for ragbits.

This module provides pluggable storage backends for different use cases:

- **Connections**: Database connection management with pooling
- **SQLStore**: Structured data storage with SQL operations
- **KVStore**: Simple key-value storage with TTL support

All storage components follow the ConfigurableComponent pattern and can be
configured via YAML or instantiated directly.

Example:
    ```python
    from ragbits.core.storage.connections import PostgresConnection, SQLiteConnection
    from ragbits.core.storage.sql_store import PostgresSQLStore, SQLiteSQLStore
    from ragbits.core.storage.kv_store import PostgresKVStore, SQLiteKVStore

    # PostgreSQL setup
    pg_conn = PostgresConnection(
        host="localhost",
        database="mydb",
        user="postgres",
        password="secret",
    )

    # Share connection across different store types
    sql_store = PostgresSQLStore(connection=pg_conn, table_prefix="app_")
    kv_store = PostgresKVStore(connection=pg_conn, table_name="app_cache")

    # SQLite setup (simpler for local development)
    sqlite_conn = SQLiteConnection(db_path="./data.db")
    sqlite_store = SQLiteSQLStore(connection=sqlite_conn)
    ```
"""

# Re-export main classes for convenience
from ragbits.core.storage.connections import DatabaseConnection
from ragbits.core.storage.kv_store import KVStore
from ragbits.core.storage.sql_store import SQLStore

__all__ = [
    "DatabaseConnection",
    "KVStore",
    "SQLStore",
]

# Optional PostgreSQL components
try:
    from ragbits.core.storage.connections import PostgresConnection  # noqa: F401
    from ragbits.core.storage.kv_store import PostgresKVStore  # noqa: F401
    from ragbits.core.storage.sql_store import PostgresSQLStore  # noqa: F401

    __all__.extend(["PostgresConnection", "PostgresKVStore", "PostgresSQLStore"])
except ImportError:
    pass

# Optional SQLite components
try:
    from ragbits.core.storage.connections import SQLiteConnection  # noqa: F401
    from ragbits.core.storage.kv_store import SQLiteKVStore  # noqa: F401
    from ragbits.core.storage.sql_store import SQLiteSQLStore  # noqa: F401

    __all__.extend(["SQLiteConnection", "SQLiteKVStore", "SQLiteSQLStore"])
except ImportError:
    pass
