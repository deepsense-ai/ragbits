"""PostgreSQL database connection implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ragbits.core.storage.connections.base import DatabaseConnection

if TYPE_CHECKING:
    import asyncpg


class PostgresConnection(DatabaseConnection["asyncpg.Connection"]):
    """PostgreSQL connection using asyncpg with connection pooling.

    Example:
        ```python
        conn = PostgresConnection(
            host="localhost",
            port=5432,
            database="mydb",
            user="postgres",
            password="secret",
        )

        async with conn:
            row = await conn.fetch_one("SELECT * FROM users WHERE id = $1", 1)
        ```
    """

    configuration_key: ClassVar = "postgres_connection"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        password: str | None = None,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ) -> None:
        """Initialize PostgreSQL connection.

        Args:
            host: Database host.
            port: Database port.
            database: Database name.
            user: Database user.
            password: Database password.
            min_pool_size: Minimum number of connections in the pool.
            max_pool_size: Maximum number of connections in the pool.
        """
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool: asyncpg.Pool | None = None
        self._initialized = False

    async def connect(self) -> None:
        """Establish the connection pool."""
        if self._pool is not None:
            return

        try:
            import asyncpg
        except ImportError as e:
            raise ImportError(
                "asyncpg is required for PostgreSQL support. " "Install it with: pip install ragbits-core[postgres]"
            ) from e

        self._pool = await asyncpg.create_pool(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password,
            min_size=self._min_pool_size,
            max_size=self._max_pool_size,
        )

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the connection pool.

        Returns:
            The asyncpg connection pool.

        Raises:
            RuntimeError: If not connected.
        """
        if self._pool is None:
            raise RuntimeError("Not connected. Call connect() or use async context manager.")
        return self._pool

    async def acquire(self) -> asyncpg.Connection:
        """Acquire a connection from the pool.

        Returns:
            An asyncpg connection.
        """
        await self._ensure_connected()
        return await self.pool.acquire()

    async def release(self, connection: asyncpg.Connection) -> None:
        """Release a connection back to the pool.

        Args:
            connection: The connection to release.
        """
        if self._pool is not None:
            await self._pool.release(connection)

    async def execute(self, query: str, *args: Any) -> Any:  # noqa: ANN401
        """Execute a query and return results.

        Args:
            query: The SQL query to execute (use $1, $2, etc. for parameters).
            *args: Query parameters.

        Returns:
            Query result status.
        """
        await self._ensure_connected()
        return await self.pool.execute(query, *args)

    async def execute_many(self, query: str, args_list: list[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters.

        Args:
            query: The SQL query to execute.
            args_list: List of parameter tuples.
        """
        await self._ensure_connected()
        await self.pool.executemany(query, args_list)

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row from the database.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            A dictionary representing the row, or None if not found.
        """
        await self._ensure_connected()
        row = await self.pool.fetchrow(query, *args)
        return dict(row) if row else None

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch all rows from the database.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            A list of dictionaries representing the rows.
        """
        await self._ensure_connected()
        rows = await self.pool.fetch(query, *args)
        return [dict(row) for row in rows]

    async def fetch_val(self, query: str, *args: Any) -> Any:  # noqa: ANN401
        """Fetch a single value from the database.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            The value from the first column of the first row.
        """
        await self._ensure_connected()
        return await self.pool.fetchval(query, *args)
