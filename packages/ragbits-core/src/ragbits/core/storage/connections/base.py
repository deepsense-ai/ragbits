"""Base database connection abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from ragbits.core import storage
from ragbits.core.utils.config_handling import WithConstructionConfig

if TYPE_CHECKING:
    from types import TracebackType


ConnectionT = TypeVar("ConnectionT")


class DatabaseConnection(WithConstructionConfig, ABC, Generic[ConnectionT]):
    """Abstract base class for database connections.

    Provides a unified interface for managing database connections with
    connection pooling, async context manager support, and lazy initialization.

    Subclasses must declare ``placeholder_style`` so that consumers can build
    portable parameterized queries:

    - ``"qmark"``: SQLite-style ``?`` placeholders.
    - ``"numeric"``: PostgreSQL-style ``$1``, ``$2`` placeholders.

    Example:
        ```python
        async with PostgresConnection(host="localhost", database="mydb") as conn:
            pool = conn.pool  # Access the underlying connection pool
        ```
    """

    default_module: ClassVar = storage
    configuration_key: ClassVar = "database_connection"

    # Placeholder style for parameterized queries; subclasses override.
    placeholder_style: ClassVar[str] = "qmark"

    _initialized: bool = False

    def placeholder(self, index: int) -> str:
        """Render a positional parameter placeholder in this dialect.

        Args:
            index: 1-based parameter index (only relevant for ``numeric``).

        Returns:
            ``"?"`` for ``qmark`` dialects, ``"$N"`` for ``numeric`` dialects.
        """
        if self.placeholder_style == "numeric":
            return f"${index}"
        return "?"

    @abstractmethod
    async def connect(self) -> None:
        """Establish the database connection or connection pool.

        This method should be idempotent - calling it multiple times
        should not create multiple connections.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection or connection pool.

        This method should be safe to call even if not connected.
        """

    @abstractmethod
    async def acquire(self) -> ConnectionT:
        """Acquire a connection from the pool.

        Returns:
            A database connection from the pool.

        Raises:
            RuntimeError: If the connection pool is not initialized.
        """

    @abstractmethod
    async def release(self, connection: ConnectionT) -> None:
        """Release a connection back to the pool.

        Args:
            connection: The connection to release.
        """

    @abstractmethod
    async def execute(self, query: str, *args: Any) -> int:  # noqa: ANN401
        """Execute a query and return the number of affected rows.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            Number of rows affected by the query (``rowcount``). For statements
            that do not affect rows (e.g. ``CREATE TABLE``) this returns ``0``.
        """

    @abstractmethod
    async def execute_many(self, query: str, args_list: list[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters.

        Args:
            query: The SQL query to execute.
            args_list: List of parameter tuples.
        """

    @abstractmethod
    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row from the database.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            A dictionary representing the row, or None if not found.
        """

    @abstractmethod
    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch all rows from the database.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            A list of dictionaries representing the rows.
        """

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Group statements into a single atomic transaction.

        Default implementation uses ``BEGIN``/``COMMIT``/``ROLLBACK``. Subclasses
        with native transaction APIs (e.g. ``asyncpg``) should override this.

        Example:
            ```python
            async with conn.transaction():
                await conn.execute("INSERT ...")
                await conn.execute("INSERT ...")
            ```
        """
        await self._ensure_connected()
        await self.execute("BEGIN")
        try:
            yield
        except BaseException:
            await self.execute("ROLLBACK")
            raise
        else:
            await self.execute("COMMIT")

    async def _ensure_connected(self) -> None:
        """Ensure the connection is established (lazy initialization)."""
        if not self._initialized:
            await self.connect()
            self._initialized = True

    async def __aenter__(self) -> DatabaseConnection[ConnectionT]:
        """Async context manager entry."""
        await self._ensure_connected()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()
        self._initialized = False
