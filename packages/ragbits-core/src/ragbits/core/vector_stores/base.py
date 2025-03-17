import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import ClassVar, TypeVar
from uuid import UUID

import pydantic
from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core import vector_stores
from ragbits.core.embeddings.base import Embedder
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent, ObjectContructionConfig
from ragbits.core.utils.pydantic import SerializableBytes

WhereQuery = dict[str, str | int | float | bool]


class VectorStoreEntry(BaseModel):
    """
    An object representing a vector database entry.
    Contains text and/or image for embedding + metadata.
    """

    id: UUID
    text: str | None = None
    image_bytes: SerializableBytes | None = None
    metadata: dict = {}

    @pydantic.model_validator(mode="after")
    def text_or_image_required(self) -> Self:
        """
        Validates that either text or image_bytes are provided.

        Raises:
            ValueError: If neither text nor image_bytes are provided.
        """
        if not self.text and not self.image_bytes:
            raise ValueError("Either text or image_bytes must be provided.")
        return self


class VectorStoreResult(BaseModel):
    """
    An object representing a query result from a vector store.
    Contains the entry, its vector, and the similarity score.
    """

    entry: VectorStoreEntry
    vector: list[float]
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

    @abstractmethod
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """

    @abstractmethod
    async def retrieve(
        self,
        text: str | None = None,
        image: bytes | None = None,
        options: VectorStoreOptionsT | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store most similar to the provided entry.
        Requires either text or image to be provided.

        Args:
            text: The text to query the vector store with.
            image: The image to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The entries.
        """

    @abstractmethod
    async def remove(self, ids: list[UUID]) -> None:
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


class EmbeddingType(Enum):
    """
    Types of embbedings supported by the vector store.
    """

    TEXT = "text"
    IMAGE = "image"


class VectorStoreWithExternalEmbedder(VectorStore[VectorStoreOptionsT]):
    """
    Base class for vector stores that takes an embedder as an argument.
    """

    def __init__(
        self,
        embedder: Embedder,
        default_options: VectorStoreOptionsT | None = None,
    ) -> None:
        """
        Constructs a new VectorStore instance.

        Args:
            embedder: The embedder to use for converting entries to vectors.
            default_options: The default options for querying the vector store.
            embedder: The embedder to use for converting entries to vectors.
        """
        super().__init__(default_options=default_options)
        self._embedder = embedder

    async def _create_embeddings(
        self, entries: list[VectorStoreEntry] | list[VectorStoreEntry]
    ) -> dict[UUID, dict[EmbeddingType, list[float]]]:
        """
        Create embeddings for the given entry.

        Args:
            entries: The entries to create embeddings for.

        Returns:
            The embeddings mapped by entry ID. The format for each entry is the same
                as the one in VectorStoreResult.vectors.
        """
        text_entries = {e.id: e.text for e in entries if e.text}
        image_entries = {e.id: e.image_bytes for e in entries if e.image_bytes}

        embeddings: defaultdict[UUID, dict[EmbeddingType, list[float]]] = defaultdict(dict)
        if text_entries:
            embedded = await self._embedder.embed_text(list(text_entries.values()))
            for i, id in enumerate(text_entries.keys()):
                embeddings[id][EmbeddingType.TEXT] = embedded[i]

        if image_entries and self._embedder.image_support():
            embedded = await self._embedder.embed_image(list(image_entries.values()))
            for i, id in enumerate(image_entries.keys()):
                embeddings[id][EmbeddingType.IMAGE] = embedded[i]

        image_only_ids = set(image_entries.keys()) - set(text_entries.keys())
        if image_only_ids and not self._embedder.image_support():
            warnings.warn(
                f"Can't embed the following image-only entries as the embedder doesn't support images: {image_only_ids}"
            )

        return dict(embeddings)

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
        options = cls.options_cls(**default_options) if default_options else None

        embedder_config = config.pop("embedder")
        embedder: Embedder = Embedder.subclass_from_config(ObjectContructionConfig.model_validate(embedder_config))

        return cls(**config, default_options=options, embedder=embedder)
