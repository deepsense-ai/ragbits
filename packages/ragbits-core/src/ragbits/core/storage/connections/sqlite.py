"""SQLite database connection implementation."""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from ragbits.core.storage.connections.base import DatabaseConnection

if TYPE_CHECKING:
    import aiosqlite


# Per-task flag: ``True`` while the running task owns the transaction lock on
# *some* SQLiteConnection. Used to:
#
# - skip re-acquiring ``_lock`` from inside ``execute``/``fetch_*`` (so the
#   caller doesn't deadlock against itself);
# - reject true call-stack nesting of :meth:`SQLiteConnection.transaction`.
_in_transaction: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_ragbits_sqlite_in_transaction",
    default=False,
)


class SQLiteConnection(DatabaseConnection["aiosqlite.Connection"]):
    """SQLite connection using aiosqlite.

    Example:
        ```python
        conn = SQLiteConnection(db_path="./data.db")

        async with conn:
            row = await conn.fetch_one("SELECT * FROM users WHERE id = ?", 1)
        ```
    """

    configuration_key: ClassVar = "sqlite_connection"
    placeholder_style: ClassVar = "qmark"

    def __init__(
        self,
        db_path: str | Path = ":memory:",
    ) -> None:
        """Initialize SQLite connection.

        Args:
            db_path: Path to the SQLite database file. Use ":memory:" for in-memory database.
        """
        self._db_path = str(db_path)
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def connect(self) -> None:
        """Establish the database connection."""
        if self._connection is not None:
            return

        try:
            import aiosqlite
        except ImportError as e:
            raise ImportError(
                "aiosqlite is required for SQLite support. " "Install it with: pip install ragbits-core[sqlite]"
            ) from e

        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the database connection.

        Returns:
            The aiosqlite connection.

        Raises:
            RuntimeError: If not connected.
        """
        if self._connection is None:
            raise RuntimeError("Not connected. Call connect() or use async context manager.")
        return self._connection

    async def acquire(self) -> aiosqlite.Connection:
        """Acquire the connection (SQLite uses a single connection).

        Returns:
            The aiosqlite connection.
        """
        await self._ensure_connected()
        return self.connection

    async def release(self, connection: aiosqlite.Connection) -> None:
        """Release the connection (no-op for SQLite single connection).

        Args:
            connection: The connection to release.
        """
        # SQLite uses a single connection, so release is a no-op

    async def execute(self, query: str, *args: Any) -> int:  # noqa: ANN401
        """Execute a query and return the number of affected rows.

        Args:
            query: The SQL query to execute (use ? for parameters).
            *args: Query parameters.

        Returns:
            ``rowcount`` as reported by the cursor (``0`` for DDL).
        """
        await self._ensure_connected()
        async with self._maybe_lock():
            cursor = await self.connection.execute(query, args)
            rowcount = cursor.rowcount
            if not _in_transaction.get():
                await self.connection.commit()
            return max(rowcount, 0)

    async def execute_many(self, query: str, args_list: list[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters.

        Args:
            query: The SQL query to execute.
            args_list: List of parameter tuples.
        """
        await self._ensure_connected()
        async with self._maybe_lock():
            await self.connection.executemany(query, args_list)
            if not _in_transaction.get():
                await self.connection.commit()

    @asynccontextmanager
    async def _maybe_lock(self) -> AsyncIterator[None]:
        """Acquire ``_lock`` only when not already inside a transaction.

        :meth:`transaction` holds ``_lock`` for its entire body so that all
        statements run on the same logical "session". Inner
        ``execute``/``fetch_*`` calls in the same task must therefore skip
        re-acquiring it to avoid a deadlock against themselves; calls from
        unrelated tasks do still acquire the lock and wait.
        """
        if _in_transaction.get():
            yield
            return
        async with self._lock:
            yield

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch a single row from the database.

        Args:
            query: The SQL query to execute.
            *args: Query parameters.

        Returns:
            A dictionary representing the row, or None if not found.
        """
        await self._ensure_connected()
        async with self._maybe_lock():
            cursor = await self.connection.execute(query, args)
            row = await cursor.fetchone()
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
        async with self._maybe_lock():
            cursor = await self.connection.execute(query, args)
            rows = await cursor.fetchall()
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
        async with self._maybe_lock():
            cursor = await self.connection.execute(query, args)
            row = await cursor.fetchone()
            return row[0] if row else None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Group statements into a single ``BEGIN``/``COMMIT`` block.

        - Concurrent calls from different tasks serialize on the connection
          lock — SQLite is single-writer anyway.
        - Nesting (re-entering ``transaction()`` from inside its own body)
          raises :class:`RuntimeError` rather than dead-locking.
        """
        await self._ensure_connected()
        if _in_transaction.get():
            raise RuntimeError("SQLiteConnection.transaction() does not support nesting")
        async with self._lock:
            token = _in_transaction.set(True)
            try:
                await self.connection.execute("BEGIN")
                try:
                    yield
                except BaseException:
                    await self.connection.rollback()
                    raise
                else:
                    await self.connection.commit()
            finally:
                _in_transaction.reset(token)
