"""Base SQL store abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from ragbits.core import storage
from ragbits.core.utils.config_handling import WithConstructionConfig

if TYPE_CHECKING:
    from types import TracebackType

    from ragbits.core.storage.connections.base import DatabaseConnection


ConnectionT = TypeVar("ConnectionT")


class SQLStore(WithConstructionConfig, ABC, Generic[ConnectionT]):
    """Abstract base class for SQL stores.

    Provides a unified interface for executing SQL operations with
    automatic schema management and connection handling.

    Example:
        ```python
        store = PostgresSQLStore(
            connection=PostgresConnection(...),
            table_prefix="myapp_",
        )

        async with store:
            await store.execute("INSERT INTO myapp_users (name) VALUES ($1)", "Alice")
            users = await store.fetch_all("SELECT * FROM myapp_users")
        ```
    """

    default_module: ClassVar = storage
    configuration_key: ClassVar = "sql_store"

    # Subclasses should define their schema creation SQL
    _schema_sql: ClassVar[str] = ""

    def __init__(
        self,
        connection: DatabaseConnection[ConnectionT],
        table_prefix: str = "",
    ) -> None:
        """Initialize SQL store.

        Args:
            connection: Database connection to use.
            table_prefix: Prefix for all table names (useful for namespacing).
        """
        self._connection = connection
        self._table_prefix = table_prefix
        self._schema_initialized = False

    @property
    def connection(self) -> DatabaseConnection[ConnectionT]:
        """Get the underlying database connection."""
        return self._connection

    @property
    def table_prefix(self) -> str:
        """Get the table prefix."""
        return self._table_prefix

    def _prefixed_table(self, name: str) -> str:
        """Get a table name with the prefix applied.

        Args:
            name: Base table name.

        Returns:
            Prefixed table name.
        """
        return f"{self._table_prefix}{name}"

    @abstractmethod
    async def _create_schema(self) -> None:
        """Create the database schema.

        This method should create all necessary tables, indexes, etc.
        It should be idempotent (safe to call multiple times).
        """

    async def _ensure_schema(self) -> None:
        """Ensure the schema is initialized (lazy initialization)."""
        if not self._schema_initialized:
            await self._create_schema()
            self._schema_initialized = True

    async def execute(self, query: str, *args: Any) -> Any:  # noqa: ANN401
        """Execute a query.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            Query result (implementation-specific).
        """
        await self._ensure_schema()
        return await self._connection.execute(query, *args)

    async def execute_many(self, query: str, args_list: list[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters.

        Args:
            query: SQL query to execute.
            args_list: List of parameter tuples.
        """
        await self._ensure_schema()
        await self._connection.execute_many(query, args_list)

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            Row as dictionary, or None if not found.
        """
        await self._ensure_schema()
        return await self._connection.fetch_one(query, *args)

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch all rows.

        Args:
            query: SQL query to execute.
            *args: Query parameters.

        Returns:
            List of rows as dictionaries.
        """
        await self._ensure_schema()
        return await self._connection.fetch_all(query, *args)

    async def __aenter__(self) -> SQLStore[ConnectionT]:
        """Async context manager entry."""
        await self._connection._ensure_connected()
        await self._ensure_schema()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self._connection.disconnect()
