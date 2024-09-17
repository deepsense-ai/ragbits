import abc
from typing import List

from pydantic import BaseModel


class VectorDBEntry(BaseModel):
    """
    An object representing a vector database entry.
    """

    key: str
    vector: list[float]
    metadata: dict


class VectorStore(abc.ABC):
    """
    A class with an implementation of Vector Store, allowing to store and retrieve vectors by similarity function.
    """

    @abc.abstractmethod
    async def store(self, entries: List[VectorDBEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """

    @abc.abstractmethod
    async def retrieve(self, vector: list[float], k: int = 5) -> list[VectorDBEntry]:
        """
        Retrieve entries from the vector store.

        Args:
            vector: The vector to search for.
            k: The number of entries to retrieve.

        Returns:
            The entries.
        """
