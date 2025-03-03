from collections.abc import Iterable
from itertools import islice

import numpy as np

from ragbits.core.audit import traceable
from ragbits.core.embeddings.base import Embedder
from ragbits.core.vector_stores.base import (
    VectorStoreEntry,
    VectorStoreNeedingEmbedder,
    VectorStoreOptions,
    VectorStoreResult,
    WhereQuery,
)


class InMemoryVectorStore(VectorStoreNeedingEmbedder[VectorStoreOptions]):
    """
    A simple in-memory implementation of Vector Store, storing vectors in memory.
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        embedder: Embedder,
        default_options: VectorStoreOptions | None = None,
        embedding_name_text: str = "text",
        embedding_name_image: str = "image",
    ) -> None:
        """
        Constructs a new InMemoryVectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            embedder: The embedder to use for converting entries to vectors.
            embedding_name_text: The name under which the text embedding is stored in the resulting object.
            embedding_name_image: The name under which the image embedding is stored in the resulting object.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
            embedding_name_text=embedding_name_text,
            embedding_name_image=embedding_name_image,
        )
        self._entries: dict[str, VectorStoreEntry] = {}
        self._embeddings: dict[str, dict[str, list[float]]] = {}

    @traceable
    async def store(self, entries: Iterable[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        for entry in entries:
            self._entries[entry.id] = entry
        embeddings = await self._create_embeddings(entries)
        self._embeddings.update(embeddings)

    @traceable
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
        (if both are avialiable chooses the one with the smallest distance).

        Args:
            text: The text to query the vector store with.
            image: The image to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The entries.
        """
        merged_options = (self.default_options | options) if options else self.default_options

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
            distances = [float(np.linalg.norm(np.array(v) - np.array(vector))) for v in vectors.values()]
            result = VectorStoreResult(entry=self._entries[entry_id], vectors=vectors, score=min(distances))
            if merged_options.max_distance is None or result.score <= merged_options.max_distance:
                results.append(result)

        results = sorted(results, key=lambda r: r.score)
        return results[: merged_options.k]

    @traceable
    async def remove(self, ids: list[str]) -> None:
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
