import numpy as np

from ragbits.core.vector_store.base import VectorDBEntry, VectorStore


class InMemoryVectorStore(VectorStore):
    """
    A simple in-memory implementation of Vector Store, storing vectors in memory.
    """

    def __init__(self) -> None:
        self._storage: dict[str, VectorDBEntry] = {}

    async def store(self, entries: list[VectorDBEntry]) -> None:
        """Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        for entry in entries:
            self._storage[entry.key] = entry

    async def retrieve(self, vector: list[float], k: int = 5) -> list[VectorDBEntry]:
        """Retrieve entries from the vector store.

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
        return np.linalg.norm(np.array(vector_x) - np.array(vector_b))
