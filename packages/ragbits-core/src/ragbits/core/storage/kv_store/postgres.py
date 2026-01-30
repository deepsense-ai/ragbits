"""PostgreSQL key-value store implementation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar

from ragbits.core.storage.kv_store.base import KVStore

if TYPE_CHECKING:
    from types import TracebackType

    from ragbits.core.storage.connections.postgres import PostgresConnection


class PostgresKVStore(KVStore[dict[str, Any]]):
    """PostgreSQL-backed key-value store with JSON values.

    Uses JSONB for efficient storage and querying of JSON values.
    Supports optional TTL (time-to-live) for automatic expiration.

    Example:
        ```python
        from ragbits.core.storage.connections import PostgresConnection
        from ragbits.core.storage.kv_store import PostgresKVStore

        conn = PostgresConnection(host="localhost", database="mydb")
        store = PostgresKVStore(connection=conn, table_name="app_cache")

        async with store:
            await store.set("config", {"debug": True}, ttl_seconds=3600)
            config = await store.get("config")
        ```
    """

    configuration_key: ClassVar = "postgres_kv_store"

    def __init__(
        self,
        connection: PostgresConnection,
        table_name: str = "kv_store",
    ) -> None:
        """Initialize PostgreSQL KV store.

        Args:
            connection: PostgreSQL connection to use.
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
                value JSONB NOT NULL,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
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
        row = await self._connection.fetch_one(
            f"""
            SELECT value FROM {self._table_name}
            WHERE key = $1
            AND (expires_at IS NULL OR expires_at > NOW())
            """,  # noqa: S608
            key,
        )
        if row:
            value = row["value"]
            # asyncpg returns JSONB as Python dict already
            if isinstance(value, str):
                return json.loads(value)
            return value
        return None

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        """Set a value for a key.

        Args:
            key: The key to set.
            value: The JSON value to store.
            ttl_seconds: Optional time-to-live in seconds.
        """
        await self._ensure_schema()
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(timezone.utc).timestamp() + ttl_seconds

        await self._connection.execute(
            f"""
            INSERT INTO {self._table_name} (key, value, expires_at, updated_at)
            VALUES ($1, $2, TO_TIMESTAMP($3), NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            """,  # noqa: S608
            key,
            json.dumps(value),
            expires_at,
        )

    async def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        await self._ensure_schema()
        result = await self._connection.execute(
            f"DELETE FROM {self._table_name} WHERE key = $1",  # noqa: S608
            key,
        )
        # asyncpg returns "DELETE N" where N is the count
        return result and "DELETE 1" in str(result)

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check.

        Returns:
            True if the key exists and is not expired.
        """
        await self._ensure_schema()
        row = await self._connection.fetch_one(
            f"""
            SELECT 1 FROM {self._table_name}
            WHERE key = $1
            AND (expires_at IS NULL OR expires_at > NOW())
            """,  # noqa: S608
            key,
        )
        return row is not None

    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").
                     Uses SQL LIKE pattern matching (% for *, _ for ?).

        Returns:
            List of matching keys.
        """
        await self._ensure_schema()
        # Convert glob pattern to SQL LIKE pattern
        sql_pattern = pattern.replace("*", "%").replace("?", "_")
        rows = await self._connection.fetch_all(
            f"""
            SELECT key FROM {self._table_name}
            WHERE key LIKE $1
            AND (expires_at IS NULL OR expires_at > NOW())
            """,  # noqa: S608
            sql_pattern,
        )
        return [row["key"] for row in rows]

    async def cleanup_expired(self) -> int:
        """Remove all expired keys.

        Returns:
            Number of keys removed.
        """
        await self._ensure_schema()
        result = await self._connection.execute(
            f"DELETE FROM {self._table_name} WHERE expires_at IS NOT NULL AND expires_at <= NOW()"  # noqa: S608
        )
        # Parse "DELETE N" to get count
        if result:
            parts = str(result).split()
            if len(parts) >= 2:  # noqa: PLR2004
                try:
                    return int(parts[1])
                except ValueError:
                    pass
        return 0

    async def __aenter__(self) -> PostgresKVStore:
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
