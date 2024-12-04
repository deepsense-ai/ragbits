from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core import vector_stores
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig, WithConstructionConfig

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


class VectorStore(WithConstructionConfig, ABC):
    """
    A class with an implementation of Vector Store, allowing to store and retrieve vectors by similarity function.
    """

    default_module: ClassVar = vector_stores

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
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        default_options = config.pop("default_options", None)
        options = VectorStoreOptions(**default_options) if default_options else None

        store_config = config.pop("metadata_store", None)
        store = (
            MetadataStore.subclass_from_config(ObjectContructionConfig.model_validate(store_config))
            if store_config
            else None
        )

        return cls(**config, default_options=options, metadata_store=store)

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
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
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
