from itertools import islice

import numpy as np

from ragbits.core.audit import traceable
from ragbits.core.embeddings import Embeddings, EmbeddingType
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.core.vector_stores.base import (
    VectorStore,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    WhereQuery,
)


class InMemoryVectorStore(VectorStore[VectorStoreOptions]):
    """
    A simple in-memory implementation of Vector Store, storing vectors in memory.
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
        default_embedder: Embeddings | None = None,
    ) -> None:
        """
        Constructs a new InMemoryVectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use.
            default_embedder: The default embedder to use for converting entries to vectors.
        """
        super().__init__(
            default_options=default_options, metadata_store=metadata_store, default_embedder=default_embedder
        )
        self._storage: dict[str, tuple[VectorStoreEntry, dict[str, list[float]]]] = {}

    @classmethod
    def from_config(cls, config: dict) -> "InMemoryVectorStore":
        """
        Creates and returns an instance of the InMemoryVectorStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the InMemoryVectorStore instance.

        Returns:
            An initialized instance of the InMemoryVectorStore class.

        Raises:
            ValidationError: The metadata_store configuration doesn't follow the expected format.
            InvalidConfigError: The metadata_store class can't be found or is not the correct type.
        """
        store = (
            MetadataStore.subclass_from_config(ObjectContructionConfig.model_validate(config["metadata_store"]))
            if "metadata_store" in config
            else None
        )

        embedder = (
            Embeddings.subclass_from_config(ObjectContructionConfig.model_validate(config["default_embedder"]))
            if "default_embedder" in config
            else None
        )

        return cls(
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=store,
            default_embedder=embedder,
        )

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store. The implementation will use default_embedder to convert
                    these entries to vectors.
        """
        if not entries:
            return

        if not self._default_embedder:
            raise ValueError("No default embedder provided for InMemoryVectorStore")

        vectors_map = {}
        for entry in entries:
            entry_vectors = {}
            if entry.text is not None:
                text_vectors = await self._default_embedder.embed_text([entry.text])
                entry_vectors[str(EmbeddingType.TEXT)] = text_vectors[0]

            if entry.image_bytes is not None and self._default_embedder.image_support():
                image_vectors = await self._default_embedder.embed_image([entry.image_bytes])
                entry_vectors[str(EmbeddingType.IMAGE)] = image_vectors[0]

            if entry_vectors:
                vectors_map[entry.id] = entry_vectors

        for entry in entries:
            if entry.id in vectors_map:
                self._storage[entry.id] = (entry, vectors_map[entry.id])

    @traceable
    async def retrieve(
        self, query: VectorStoreEntry, options: VectorStoreOptions | None = None
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store.

        Args:
            query: The query entry to search for. The implementation will use default_embedder
                  to convert this entry to vector(s).
            options: The options for querying the vector store.

        Returns:
            The results, containing entries, their vectors and similarity scores.
        """
        if not self._default_embedder:
            raise ValueError("No default embedder provided for InMemoryVectorStore")

        merged_options = (self.default_options | options) if options else self.default_options
        query_vectors = {}

        if query.text is not None:
            text_vectors = await self._default_embedder.embed_text([query.text])
            query_vectors[str(EmbeddingType.TEXT)] = text_vectors[0]

        if query.image_bytes is not None and self._default_embedder.image_support():
            image_vectors = await self._default_embedder.embed_image([query.image_bytes])
            query_vectors[str(EmbeddingType.IMAGE)] = image_vectors[0]

        if not query_vectors:
            return []

        # For each entry, compute the minimum distance across all available vector types
        entries_with_scores = []
        for entry, vectors in self._storage.values():
            min_distance = float("inf")
            for vector_type, query_vector in query_vectors.items():
                if vector_type in vectors:
                    distance = float(np.linalg.norm(np.array(vectors[vector_type]) - np.array(query_vector)))
                    min_distance = min(min_distance, distance)
            if min_distance != float("inf"):
                entries_with_scores.append((entry, vectors, min_distance))

        # Sort by distance and apply k/max_distance filters
        entries_with_scores.sort(key=lambda x: x[2])
        results = []
        for entry, vectors, distance in entries_with_scores[: merged_options.k]:
            if merged_options.max_distance is None or distance <= merged_options.max_distance:
                results.append(VectorStoreResult(entry=entry, vectors=vectors, score=1.0 - distance))

        return results

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        for id in ids:
            del self._storage[id]

    @traceable
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
        entries = iter(entry for entry, _ in self._storage.values())

        if where:
            entries = (
                entry for entry in entries if all(entry.metadata.get(key) == value for key, value in where.items())
            )

        if offset:
            entries = islice(entries, offset, None)

        if limit:
            entries = islice(entries, limit)

        return list(entries)
