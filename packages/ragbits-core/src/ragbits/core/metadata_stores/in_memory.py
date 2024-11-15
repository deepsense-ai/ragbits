from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.metadata_stores.exceptions import MetadataNotFoundError


class InMemoryMetadataStore(MetadataStore):
    """
    Metadata Store implemented in memory
    """

    def __init__(self) -> None:
        """
        Constructs a new InMemoryMetadataStore instance.
        """
        self._storage: dict[str, dict] = {}

    @traceable
    async def store(self, ids: list[str], metadatas: list[dict]) -> None:
        """
        Store metadatas under ids in metadata store.

        Args:
            ids: list of unique ids of the entries
            metadatas: list of dicts with metadata.
        """
        for _id, metadata in zip(ids, metadatas, strict=True):
            self._storage[_id] = metadata

    @traceable
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
        try:
            return [self._storage[_id] for _id in ids]
        except KeyError as exc:
            raise MetadataNotFoundError(*exc.args) from exc
