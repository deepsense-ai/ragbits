from itertools import islice
from uuid import UUID

import numpy as np

from ragbits.core.audit import trace, traceable
from ragbits.core.embeddings.base import Embedder
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    VectorStoreWithExternalEmbedder,
    WhereQuery,
)


class InMemoryVectorStore(VectorStoreWithExternalEmbedder[VectorStoreOptions]):
    """
    A simple in-memory implementation of Vector Store, storing vectors in memory.
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        embedder: Embedder,
        default_options: VectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new InMemoryVectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            embedder: The embedder to use for converting entries to vectors.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
        )
        self._entries: dict[UUID, VectorStoreEntry] = {}
        self._embeddings: dict[UUID, dict[EmbeddingType, list[float]]] = {}

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        with trace(
            entries=entries,
            embedder=repr(self._embedder),
        ) as outputs:
            for entry in entries:
                self._entries[entry.id] = entry
            embeddings = await self._create_embeddings(entries)
            self._embeddings.update(embeddings)
            outputs.embeddings = self._embeddings
            outputs.entries = self._entries

    async def retrieve(
        self,
        text: str | None = None,
        image: bytes | None = None,
        options: VectorStoreOptions | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store most similar to the provided entry.
        Requires either text or image to be provided.

        Compare stored entries looking both at their text and image embeddings
        (if both are available chooses the one with the smallest distance).

        Args:
            text: The text to query the vector store with.
            image: The image to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The entries.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(text=text, image=image, options=merged_options.dict(), embedder=repr(self._embedder)) as outputs:
            if image and text:
                raise ValueError("Either text or image should be provided, not both.")

            if text:
                vector = await self._embedder.embed_text([text])
            elif image:
                vector = await self._embedder.embed_image([image])
            else:
                raise ValueError("Either text or image should be provided.")

            results: list[VectorStoreResult] = []

            for entry_id, vectors in self._embeddings.items():
                distances = [
                    (float(np.linalg.norm(np.array(v) - np.array(vector))), embedding_type)
                    for embedding_type, v in vectors.items()
                ]
                min_distance, min_type = min(distances, key=lambda x: x[0])
                result = VectorStoreResult(entry=self._entries[entry_id], vector=vectors[min_type], score=min_distance)
                if merged_options.max_distance is None or result.score <= merged_options.max_distance:
                    results.append(result)

            outputs.results = sorted(results, key=lambda r: r.score)[: merged_options.k]
            return outputs.results

    @traceable
    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        for id in ids:
            del self._entries[id]
            del self._embeddings[id]

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
        entries = iter(self._entries.values())

        if where:
            entries = (
                entry for entry in entries if all(entry.metadata.get(key) == value for key, value in where.items())
            )

        if offset:
            entries = islice(entries, offset, None)

        if limit:
            entries = islice(entries, limit)

        return list(entries)
