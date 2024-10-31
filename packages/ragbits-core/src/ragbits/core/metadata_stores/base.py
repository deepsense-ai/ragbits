from abc import ABC, abstractmethod


class MetadataStore(ABC):
    """
    An abstract class for metadata storage. Allows to store, query and retrieve metadata in form of key value pairs.
    """

    @abstractmethod
    async def store(self, ids: list[str], metadatas: list[dict]) -> None:
        """
        Store metadatas under ids in metadata store.

        Args:
            ids: list of unique ids of the entries
            metadatas: list of dicts with metadata.
        """

    @abstractmethod
    async def get(self, ids: list[str]) -> list[dict]:
        """
        Returns metadatas associated with a given ids.

        Args:
            ids: list of ids to use.

        Returns:
            List of metadata dicts associated with a given ids.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
