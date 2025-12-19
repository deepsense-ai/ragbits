"""Base database connection abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
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

    Example:
        ```python
        async with PostgresConnection(host="localhost", database="mydb") as conn:
            pool = conn.pool  # Access the underlying connection pool
        ```
    """

    default_module: ClassVar = storage
    configuration_key: ClassVar = "database_connection"

    _initialized: bool = False

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
    async def execute(self, query: str, *args: Any) -> Any:  # noqa: ANN401
        """Execute a query and return results.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            Query results (implementation-specific).
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
