"""SQLite key-value store implementation."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, ClassVar

from ragbits.core.storage.kv_store.base import KVStore

if TYPE_CHECKING:
    from types import TracebackType

    from ragbits.core.storage.connections.sqlite import SQLiteConnection


class SQLiteKVStore(KVStore[dict[str, Any]]):
    """SQLite-backed key-value store with JSON values.

    Stores JSON values as TEXT with optional TTL support.

    Example:
        ```python
        from ragbits.core.storage.connections import SQLiteConnection
        from ragbits.core.storage.kv_store import SQLiteKVStore

        conn = SQLiteConnection(db_path="./cache.db")
        store = SQLiteKVStore(connection=conn, table_name="app_cache")

        async with store:
            await store.set("config", {"debug": True}, ttl_seconds=3600)
            config = await store.get("config")
        ```
    """

    configuration_key: ClassVar = "sqlite_kv_store"

    def __init__(
        self,
        connection: SQLiteConnection,
        table_name: str = "kv_store",
    ) -> None:
        """Initialize SQLite KV store.

        Args:
            connection: SQLite connection to use.
            table_name: Name of the table for storing key-value pairs.
        """
        self._connection = connection
        self._table_name = table_name
        self._schema_initialized = False

    async def _ensure_schema(self) -> None:
        """Create the KV table if it doesn't exist."""
        if self._schema_initialized:
            return

        await self._connection._ensure_connected()
        await self._connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
            """  # noqa: S608
        )
        # Index for TTL cleanup
        await self._connection.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expires
            ON {self._table_name} (expires_at)
            WHERE expires_at IS NOT NULL
            """  # noqa: S608
        )
        self._schema_initialized = True

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a value by key.

        Args:
            key: The key to look up.

        Returns:
            The value if found and not expired, None otherwise.
        """
        await self._ensure_schema()
        now = time.time()
        row = await self._connection.fetch_one(
            f"""
            SELECT value FROM {self._table_name}
            WHERE key = ?
            AND (expires_at IS NULL OR expires_at > ?)
            """,  # noqa: S608
            key,
            now,
        )
        if row:
            return json.loads(row["value"])
        return None

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        """Set a value for a key.

        Args:
            key: The key to set.
            value: The JSON value to store.
            ttl_seconds: Optional time-to-live in seconds.
        """
        await self._ensure_schema()
        now = time.time()
        expires_at = None
        if ttl_seconds is not None:
            expires_at = now + ttl_seconds

        await self._connection.execute(
            f"""
            INSERT INTO {self._table_name} (key, value, expires_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (key) DO UPDATE SET
                value = excluded.value,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            """,  # noqa: S608
            key,
            json.dumps(value),
            expires_at,
            now,
        )

    async def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        await self._ensure_schema()
        # First check if key exists
        exists = await self.exists(key)
        if exists:
            await self._connection.execute(
                f"DELETE FROM {self._table_name} WHERE key = ?",  # noqa: S608
                key,
            )
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check.

        Returns:
            True if the key exists and is not expired.
        """
        await self._ensure_schema()
        now = time.time()
        row = await self._connection.fetch_one(
            f"""
            SELECT 1 FROM {self._table_name}
            WHERE key = ?
            AND (expires_at IS NULL OR expires_at > ?)
            """,  # noqa: S608
            key,
            now,
        )
        return row is not None

    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").
                     Uses SQLite GLOB pattern matching.

        Returns:
            List of matching keys.
        """
        await self._ensure_schema()
        now = time.time()
        rows = await self._connection.fetch_all(
            f"""
            SELECT key FROM {self._table_name}
            WHERE key GLOB ?
            AND (expires_at IS NULL OR expires_at > ?)
            """,  # noqa: S608
            pattern,
            now,
        )
        return [row["key"] for row in rows]

    async def cleanup_expired(self) -> int:
        """Remove all expired keys.

        Returns:
            Number of keys removed.
        """
        await self._ensure_schema()
        now = time.time()
        # Count before delete
        row = await self._connection.fetch_one(
            f"SELECT COUNT(*) as cnt FROM {self._table_name} WHERE expires_at IS NOT NULL AND expires_at <= ?",  # noqa: S608
            now,
        )
        count = row["cnt"] if row else 0

        await self._connection.execute(
            f"DELETE FROM {self._table_name} WHERE expires_at IS NOT NULL AND expires_at <= ?",  # noqa: S608
            now,
        )
        return count

    async def __aenter__(self) -> SQLiteKVStore:
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
