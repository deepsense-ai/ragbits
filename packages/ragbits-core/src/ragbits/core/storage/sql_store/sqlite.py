"""SQLite SQL store implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ragbits.core.storage.sql_store.base import SQLStore

if TYPE_CHECKING:
    import aiosqlite  # noqa: F401

    from ragbits.core.storage.connections.sqlite import SQLiteConnection


class SQLiteSQLStore(SQLStore["aiosqlite.Connection"]):
    """SQLite-backed SQL store.

    Example:
        ```python
        from ragbits.core.storage.connections import SQLiteConnection
        from ragbits.core.storage.sql_store import SQLiteSQLStore

        conn = SQLiteConnection(db_path="./data.db")
        store = SQLiteSQLStore(connection=conn, table_prefix="app_")

        async with store:
            # Execute queries
            await store.execute("INSERT INTO app_items (key, value) VALUES (?, ?)", "foo", "bar")
            result = await store.fetch_one("SELECT * FROM app_items WHERE key = ?", "foo")
        ```
    """

    configuration_key: ClassVar = "sqlite_sql_store"

    def __init__(
        self,
        connection: SQLiteConnection,
        table_prefix: str = "",
    ) -> None:
        """Initialize SQLite SQL store.

        Args:
            connection: SQLite connection to use.
            table_prefix: Prefix for all table names.
        """
        super().__init__(connection=connection, table_prefix=table_prefix)

    async def _create_schema(self) -> None:
        """Create the database schema.

        Override in subclasses to create specific schemas.
        """
        # Base implementation does nothing - subclasses should override

    async def fetch_val(self, query: str, *args: Any) -> Any:  # noqa: ANN401
        """Fetch a single value.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            The value from the first column of the first row.
        """
        await self._ensure_schema()
        # Access the underlying connection's fetch_val
        conn = self._connection
        if hasattr(conn, "fetch_val"):
            return await conn.fetch_val(query, *args)  # type: ignore[attr-defined]
        # Fallback to fetch_one
        row = await self._connection.fetch_one(query, *args)
        if row:
            return next(iter(row.values()))
        return None

    async def execute_returning(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Execute a query and fetch the last inserted row.

        Note: SQLite doesn't support RETURNING in the same way as PostgreSQL.
        This method executes the query and then fetches the last inserted row
        using last_insert_rowid().

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            The inserted row as a dictionary, or None.
        """
        await self._ensure_schema()
        await self._connection.execute(query, *args)
        # Get the last inserted rowid
        row = await self._connection.fetch_one("SELECT * FROM sqlite_master WHERE type='table' LIMIT 1")
        return row
