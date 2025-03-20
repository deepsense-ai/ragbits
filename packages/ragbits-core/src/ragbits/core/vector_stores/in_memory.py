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
        embedding_type: EmbeddingType = EmbeddingType.TEXT,
        default_options: VectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new InMemoryVectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            embedder: The embedder to use for converting entries to vectors.
            embedding_type: Which part of the entry to embed, either text or image. The other part will be ignored.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
            embedding_type=embedding_type,
        )
        self._entries: dict[UUID, VectorStoreEntry] = {}
        self._embeddings: dict[UUID, list[float]] = {}

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        with trace(
            entries=entries,
            embedder=repr(self._embedder),
            embedding_type=self._embedding_type,
        ) as outputs:
            embeddings = await self._create_embeddings(entries)
            self._embeddings.update(embeddings)
            self._entries.update({entry.id: entry for entry in entries if entry.id in embeddings})
            outputs.embeddings = self._embeddings
            outputs.entries = self._entries

    async def retrieve(
        self,
        text: str,
        options: VectorStoreOptions | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store most similar to the provided text.

        Args:
            text: The text to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The entries.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            text=text,
            options=merged_options.dict(),
            embedder=repr(self._embedder),
            embedding_type=self._embedding_type,
        ) as outputs:
            query_vector = await self._embedder.embed_text([text])
            results: list[VectorStoreResult] = []

            for entry_id, vector in self._embeddings.items():
                distance = float(np.linalg.norm(np.array(vector) - np.array(query_vector)))
                result = VectorStoreResult(entry=self._entries[entry_id], vector=vector, score=distance)
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

        entries = (entry for entry in entries if entry.id in self._embeddings)

        if where:
            entries = (
                entry for entry in entries if all(entry.metadata.get(key) == value for key, value in where.items())
            )

        if offset:
            entries = islice(entries, offset, None)

        if limit:
            entries = islice(entries, limit)

        return list(entries)
