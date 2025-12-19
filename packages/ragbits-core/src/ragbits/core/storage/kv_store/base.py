"""Base key-value store abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from ragbits.core import storage
from ragbits.core.utils.config_handling import WithConstructionConfig

if TYPE_CHECKING:
    from types import TracebackType


ValueT = TypeVar("ValueT")


class KVStore(WithConstructionConfig, ABC, Generic[ValueT]):
    """Abstract base class for key-value stores.

    Provides a simple key-value interface with support for different
    value types (strings, JSON, binary) and optional TTL.

    Example:
        ```python
        store = PostgresKVStore(
            connection=PostgresConnection(...),
            table_name="app_cache",
        )

        async with store:
            await store.set("user:123", {"name": "Alice", "age": 30})
            user = await store.get("user:123")
            await store.delete("user:123")
        ```
    """

    default_module: ClassVar = storage
    configuration_key: ClassVar = "kv_store"

    @abstractmethod
    async def get(self, key: str) -> ValueT | None:
        """Get a value by key.

        Args:
            key: The key to look up.

        Returns:
            The value if found, None otherwise.
        """

    @abstractmethod
    async def set(self, key: str, value: ValueT, ttl_seconds: int | None = None) -> None:
        """Set a value for a key.

        Args:
            key: The key to set.
            value: The value to store.
            ttl_seconds: Optional time-to-live in seconds.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check.

        Returns:
            True if the key exists.
        """

    @abstractmethod
    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").

        Returns:
            List of matching keys.
        """

    async def get_many(self, keys: list[str]) -> dict[str, ValueT | None]:
        """Get multiple values by keys.

        Args:
            keys: List of keys to look up.

        Returns:
            Dictionary mapping keys to values (None for missing keys).
        """
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result

    async def set_many(self, items: dict[str, ValueT], ttl_seconds: int | None = None) -> None:
        """Set multiple key-value pairs.

        Args:
            items: Dictionary of key-value pairs to set.
            ttl_seconds: Optional time-to-live in seconds (applies to all).
        """
        for key, value in items.items():
            await self.set(key, value, ttl_seconds)

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys.

        Args:
            keys: List of keys to delete.

        Returns:
            Number of keys deleted.
        """
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count

    @abstractmethod
    async def __aenter__(self) -> KVStore[ValueT]:
        """Async context manager entry."""

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
