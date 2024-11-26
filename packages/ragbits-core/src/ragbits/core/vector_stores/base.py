from abc import ABC, abstractmethod

from pydantic import BaseModel

from ragbits.core.metadata_stores.base import MetadataStore

WhereQuery = dict[str, str | int | float | bool]


class VectorStoreEntry(BaseModel):
    """
    An object representing a vector database entry.
    """

    id: str
    key: str
    vector: list[float]
    metadata: dict


class VectorStoreOptions(BaseModel, ABC):
    """
    An object representing the options for the vector store.
    """

    k: int = 5
    max_distance: float | None = None


class VectorStore(ABC):
    """
    A class with an implementation of Vector Store, allowing to store and retrieve vectors by similarity function.
    """

    def __init__(
        self,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new VectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use.
        """
        super().__init__()
        self._default_options = default_options or VectorStoreOptions()
        self._metadata_store = metadata_store

    @classmethod
    def from_config(cls, config: dict) -> "VectorStore":
        """
        Creates and returns an instance of the Reranker class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the Reranker instance.

        Returns:
            An initialized instance of the Reranker class.

        Raises:
            NotImplementedError: If the class cannot be created from the provided configuration.
        """
        raise NotImplementedError(f"Cannot create class {cls.__name__} from config.")

    @abstractmethod
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """

    @abstractmethod
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieve entries from the vector store.

        Args:
            vector: The vector to search for.
            options: The options for querying the vector store.

        Returns:
            The entries.
        """

    @abstractmethod
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
