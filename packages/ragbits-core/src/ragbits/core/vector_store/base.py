import abc

from pydantic import BaseModel


class VectorDBEntry(BaseModel):
    """
    An object representing a vector database entry.
    """

    key: str
    vector: list[float]
    metadata: dict


WhereQuery = dict[str, str | int | float | bool]


class VectorStore(abc.ABC):
    """
    A class with an implementation of Vector Store, allowing to store and retrieve vectors by similarity function.
    """

    @abc.abstractmethod
    async def store(self, entries: list[VectorDBEntry]) -> None:
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

    @abc.abstractmethod
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
