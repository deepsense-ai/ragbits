import abc
from typing import Any
from uuid import UUID


class MetadataStore(abc.ABC):
    """
    An abstract class for metadata storage. Allows to store, query and retrieve metadata in form of key value pairs
    """

    @abc.abstractmethod
    async def store(self, key: str | UUID, metadata: dict) -> None:
        """
        Store metadata under key in metadata store

        Args:
            key: unique key of the entry
            metadata: dict with metadata
        """

    @abc.abstractmethod
    async def query(self, metadata_field_name: str, value: Any) -> dict:  # noqa
        """
        Queries metastore and returns dicts with key: metadata format that match

        Args:
            metadata_field_name: name of metadata field
            value: value to match against

        Returns:
            dict with key: metadata entries that match query
        """

    @abc.abstractmethod
    async def get(self, key: str | UUID) -> dict:
        """
        Returns metadata associated with a given key

        Args:
            key: key to use

        Returns:
            metadata dict associated with a given key
        """
