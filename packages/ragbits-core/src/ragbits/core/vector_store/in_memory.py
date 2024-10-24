from itertools import islice

import numpy as np

from ragbits.core.vector_store.base import VectorDBEntry, VectorStore, WhereQuery


class InMemoryVectorStore(VectorStore):
    """
    A simple in-memory implementation of Vector Store, storing vectors in memory.
    """

    def __init__(self) -> None:
        self._storage: dict[str, VectorDBEntry] = {}

    async def store(self, entries: list[VectorDBEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        for entry in entries:
            self._storage[entry.key] = entry

    async def retrieve(self, vector: list[float], k: int = 5) -> list[VectorDBEntry]:
        """
        Retrieve entries from the vector store.

        Args:
            vector: The vector to search for.
            k: The number of entries to retrieve.

        Returns:
            The entries.
        """
        knn = []

        for entry in self._storage.values():
            entry_distance = self._calculate_squared_euclidean(entry.vector, vector)
            knn.append((entry, entry_distance))

        knn.sort(key=lambda x: x[1])

        return [entry for entry, _ in knn[:k]]

    @staticmethod
    def _calculate_squared_euclidean(vector_x: list[float], vector_b: list[float]) -> float:
        return float(np.linalg.norm(np.array(vector_x) - np.array(vector_b)))

    async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> list[VectorDBEntry]:
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
