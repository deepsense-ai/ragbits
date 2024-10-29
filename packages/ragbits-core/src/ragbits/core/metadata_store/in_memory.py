from typing import Any
from uuid import UUID

from ragbits.core.metadata_store.base import MetadataStore


class InMemoryMetadataStore(MetadataStore):
    """
    Metadata Store implemented in memory
    """

    def __init__(self) -> None:
        self._storage: dict[str | UUID, Any] = {}

    async def store(self, key: str | UUID, metadata: dict) -> None:
        """
        Store metadata under key in metadata store

        Args:
            key: unique key of the entry
            metadata: dict with metadata
        """
        self._storage[key] = metadata

    async def query(self, metadata_field_name: str, value: Any) -> dict:  # noqa
        """
        Queries metastore and returns dicts with key: metadata format that match

        Args:
            metadata_field_name: name of metadata field
            value: value to match against

        Returns:
            dict with key: metadata entries that match query
        """
        return {
            key: metadata for key, metadata in self._storage.items() if metadata.get(metadata_field_name, None) == value
        }

    async def get(self, key: str | UUID) -> dict:
        """
        Returns metadata associated with a given key

        Args:
            key: key to use

        Returns:
            metadata dict associated with a given key
        """
        return self._storage.get(key, {})
