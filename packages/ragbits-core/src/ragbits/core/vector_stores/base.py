from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core import vector_stores
from ragbits.core.embeddings import Embeddings
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent, ObjectContructionConfig

WhereQuery = dict[str, str | int | float | bool]


class VectorStoreEntry(BaseModel):
    """
    An object representing a vector database entry.
    Contains text and/or image for embedding + metadata.
    """

    id: str
    key: str
    text: str | None = None
    image_bytes: bytes | None = None
    metadata: dict


class VectorStoreResult(BaseModel):
    """
    An object representing a query result from the vector store.
    Contains the entry, its vectors, and the similarity score.
    """

    entry: VectorStoreEntry
    vectors: dict[str, list[float]]  # Maps embedding type to vector
    score: float


class VectorStoreOptions(Options):
    """
    An object representing the options for the vector store.
    """

    k: int = 5
    max_distance: float | None = None


VectorStoreOptionsT = TypeVar("VectorStoreOptionsT", bound=VectorStoreOptions)


class VectorStore(ConfigurableComponent[VectorStoreOptionsT], ABC):
    """
    A class with an implementation of Vector Store, allowing to store and retrieve vectors by similarity function.
    """

    options_cls: type[VectorStoreOptionsT]
    default_module: ClassVar = vector_stores
    configuration_key: ClassVar = "vector_store"

    def __init__(
        self,
        default_options: VectorStoreOptionsT | None = None,
        metadata_store: MetadataStore | None = None,
        default_embedder: Embeddings | None = None,
    ) -> None:
        """
        Constructs a new VectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use.
            default_embedder: The default embedder to use for converting entries to vectors.
                            This is optional and specific implementations may choose to use
                            their own embedding approach.
        """
        super().__init__(default_options=default_options)
        self._metadata_store = metadata_store
        self._default_embedder = default_embedder

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.

        Raises:
            ValidationError: The metadata_store configuration doesn't follow the expected format.
            InvalidConfigError: The metadata_store class can't be found or is not the correct type.
        """
        default_options = config.pop("default_options", None)
        options = cls.options_cls(**default_options) if default_options else None

        store_config = config.pop("metadata_store", None)
        store = (
            MetadataStore.subclass_from_config(ObjectContructionConfig.model_validate(store_config))
            if store_config
            else None
        )

        embedder_config = config.pop("default_embedder", None)
        embedder = (
            Embeddings.subclass_from_config(ObjectContructionConfig.model_validate(embedder_config))
            if embedder_config
            else None
        )

        return cls(**config, default_options=options, metadata_store=store, default_embedder=embedder)

    @abstractmethod
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store. The implementation is responsible for converting
                    these entries to vectors using appropriate embedding approach.
        """

    @abstractmethod
    async def retrieve(
        self, query: VectorStoreEntry, options: VectorStoreOptionsT | None = None
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store.

        Args:
            query: The query entry to search for. The implementation is responsible for converting
                  this entry to vector(s) using appropriate embedding approach.
            options: The options for querying the vector store.

        Returns:
            The results, containing entries, their vectors and similarity scores.
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
