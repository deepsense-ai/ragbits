from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

import httpx
from weaviate import WeaviateAsyncClient
import weaviate.classes as wvc
from weaviate.classes.config import Configure, VectorDistances
from typing_extensions import Self

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings import Embedder, SparseEmbedder, SparseVector
from ragbits.core.utils.config_handling import ObjectConstructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreOptionsT,
    VectorStoreResult,
    VectorStoreWithEmbedder,
    WhereQuery,
)


class WeaviateVectorStore(VectorStoreWithEmbedder[VectorStoreOptions]):
    """
    Vector store implementation using [Weaviate](https://weaviate.io/).
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: WeaviateAsyncClient,
        index_name: str,
        embedder: Embedder,
        embedding_type: EmbeddingType = EmbeddingType.TEXT,
        distance_method: VectorDistances = VectorDistances.COSINE,
        default_options: VectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new WeaviateVectorStore instance.

        Args:
            client: An instance of the Weaviate client.
            index_name: The name of the index.
            embedder: The embedder to use for converting entries to vectors. Can be a regular Embedder for dense vectors
                     or a SparseEmbedder for sparse vectors.
            embedding_type: Which part of the entry to embed, either text or image. The other part will be ignored.
            distance_method: The distance metric to use when creating the collection.
            default_options: The default options for querying the vector store.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
            embedding_type=embedding_type,
        )
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method
        self.is_sparse = isinstance(embedder, SparseEmbedder)
        self._vector_name = "sparse" if self.is_sparse else "dense"

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores vector entries in the Weaviate collection.

        Args:
            entries: List of VectorStoreEntry objects to store

        Raises:
            WeaviateException: If upload to collection fails.
        """
        with trace(
            entries=entries,
            index_name=self._index_name,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
            embedding_type=self._embedding_type,
        ):
            if not entries:
                return

            embeddings: dict = await self._create_embeddings(entries)

            if not await self._client.collections.exists(self._index_name):
                await self._client.collections.create(
                    name=self._index_name,
                    vectorizer_config=wvc.config.Configure.Vectorizer.none()
                )

            index = self._client.collections.get(self._index_name)

            objects = []
            for entry in entries:
                if entry.id in embeddings:
                    objects.append(wvc.data.DataObject(
                        uuid=str(entry.id),
                        properties=entry.model_dump(exclude={"id"}, exclude_none=True, mode="json"),
                        vector=embeddings[entry.id]
                    ))

            if objects:
                await index.data.insert_many(objects)

    async def retrieve(self, text: str, options: VectorStoreOptionsT | None = None) -> list[VectorStoreResult]:
        """
        Retrieves entries from the Weaviate collection based on vector similarity.

        Args:
            text: The text to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
        pass

    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.

        Raises:
            ValueError: If collection named `self._index_name` is not present in the vector store.
        """
        pass

    async def list(
        self,
        where: WhereQuery | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector store. The entries can be filtered, limited and offset.

        Args:
            where: Conditions for filtering results.
                Reference: TODO
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        pass
