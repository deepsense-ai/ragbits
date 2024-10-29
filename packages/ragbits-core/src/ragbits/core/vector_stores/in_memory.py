from itertools import islice

import numpy as np

from ragbits.core.metadata_store.base import MetadataStore
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery


class InMemoryVectorStore(VectorStore):
    """
    A simple in-memory implementation of Vector Store, storing vectors in memory.
    """

    def __init__(
        self, default_options: VectorStoreOptions | None = None, metadata_store: MetadataStore | None = None
    ) -> None:
        super().__init__(default_options, metadata_store)
        self._storage: dict[str, VectorStoreEntry] = {}

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        for entry in entries:
            self._storage[entry.key] = entry

    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieve entries from the vector store.

        Args:
            vector: The vector to search for.
            options: The options for querying the vector store.

        Returns:
            The entries.
        """
        options = self._default_options if options is None else options
        entries = sorted(
            (
                (entry, float(np.linalg.norm(np.array(entry.vector) - np.array(vector))))
                for entry in self._storage.values()
            ),
            key=lambda x: x[1],
        )
        return [
            entry
            for entry, distance in entries[: options.k]
            if options.max_distance is None or distance <= options.max_distance
        ]

    async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector store. The entries can be filtered, limited and offset.

        Args:
            where: The filter dictionary - the keys are the field names and the values are the values to filter by.
                Not specifying the key means no filtering.
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.
        """
        entries = iter(self._storage.values())

        if where:
            entries = (
                entry for entry in entries if all(entry.metadata.get(key) == value for key, value in where.items())
            )

        if offset:
            entries = islice(entries, offset, None)

        if limit:
            entries = islice(entries, limit)

        return list(entries)
