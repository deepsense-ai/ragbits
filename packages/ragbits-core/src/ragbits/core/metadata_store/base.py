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

    @abc.abstractmethod
    async def get_all(self) -> dict:
        """
        Returns all keys with associated metadata

        Returns:
            metadata dict for all entries
        """

    @abc.abstractmethod
    async def store_global(self, metadata: dict) -> None:
        """
        Store key value pairs of metadata that is shared across entries

        Args:
            metadata: common key value pairs for the whole collection
        """

    @abc.abstractmethod
    async def get_global(self) -> dict:
        """
        Get key value pairs of metadata that is shared across entries

        Returns:
            metadata for the whole collection
        """
