import contextlib
from collections.abc import Iterable, Mapping
from typing import cast
from uuid import UUID

import httpx
import qdrant_client
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.embeddings.base import Embedder
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict
from ragbits.core.vector_stores.base import (
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreOptionsT,
    VectorStoreResult,
    VectorStoreWithExternalEmbedder,
    WhereQuery,
)


class QdrantVectorStore(VectorStoreWithExternalEmbedder[VectorStoreOptions]):
    """
    Vector store implementation using [Qdrant](https://qdrant.tech).
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: AsyncQdrantClient,
        index_name: str,
        embedder: Embedder,
        distance_method: Distance = Distance.COSINE,
        default_options: VectorStoreOptions | None = None,
        embedding_name_text: str = "text",
        embedding_name_image: str = "image",
    ) -> None:
        """
        Constructs a new QdrantVectorStore instance.

        Args:
            client: An instance of the Qdrant client.
            index_name: The name of the index.
            embedder: The embedder to use for converting entries to vectors.
            distance_method: The distance metric to use when creating the collection.
            default_options: The default options for querying the vector store.
            embedding_name_text: The name under which the text embedding is stored in the resulting object.
            embedding_name_image: The name under which the image embedding is stored in the resulting object.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
            embedding_name_text=embedding_name_text,
            embedding_name_image=embedding_name_image,
        )
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        client_options = ObjectContructionConfig.model_validate(config["client"])
        client_cls = import_by_path(client_options.type, qdrant_client)
        if "limits" in client_options.config:
            limits = httpx.Limits(**client_options.config["limits"])
            client_options.config["limits"] = limits
        config["client"] = client_cls(**client_options.config)
        return super().from_config(config)

    @staticmethod
    def _detect_vector_size(vectors: Iterable[Mapping[str, list[float]]]) -> int:
        """
        Detects the size of the vectors from the input. Assumes all vectors have the same size.
        """
        for vector_map in vectors:
            for vector in vector_map.values():
                return len(vector)
        raise ValueError("No vectors found in the input")

    def _internal_id(self, entry_id: UUID, embedding_type: str) -> UUID:
        return UUID(int=entry_id.int + self._embedding_types.index(embedding_type))

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores vector entries in the Qdrant collection.

        Args:
            entries: List of VectorStoreEntry objects to store

        Raises:
            QdrantException: If upload to collection fails.
        """
        if not entries:
            return

        embeddings: dict = await self._create_embeddings(entries)

        if not await self._client.collection_exists(self._index_name):
            vector_size = self._detect_vector_size(embeddings.values())
            await self._client.create_collection(
                collection_name=self._index_name,
                vectors_config=VectorParams(size=vector_size, distance=self._distance_method),
            )

        points = (
            models.PointStruct(
                id=str(self._internal_id(entry.id, embedding_type)),
                vector=embeddings[entry.id][embedding_type],
                payload={**entry.model_dump(exclude_none=True), "__embeddings": embeddings[entry.id]},
            )
            for entry in entries
            for embedding_type in self._embedding_types
            if entry.id in embeddings and embedding_type in embeddings[entry.id]
        )

        self._client.upload_points(
            collection_name=self._index_name,
            points=points,
            wait=True,
        )

    @traceable
    async def retrieve(
        self, text: str | None = None, image: bytes | None = None, options: VectorStoreOptionsT | None = None
    ) -> list[VectorStoreResult]:
        """
        Retrieves entries from the Qdrant collection based on vector similarity.

        Args:
            text: The text to query the vector store with.
            image: The image to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        score_threshold = 1 - merged_options.max_distance if merged_options.max_distance else None

        if image and text:
            raise ValueError("Either text or image should be provided, not both.")

        if text:
            vector = await self._embedder.embed_text([text])
        elif image:
            vector = await self._embedder.embed_image([image])
        else:
            raise ValueError("Either text or image should be provided.")

        query_results = await self._client.query_points(
            collection_name=self._index_name,
            query=vector[0],
            limit=merged_options.k * 2,  # *2 to account for possible duplicates
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=True,
        )

        results: list[VectorStoreResult] = []
        seen_ids = set()
        for point in query_results.points:
            entry = VectorStoreEntry.model_validate(point.payload)
            if entry.id in seen_ids:
                continue
            seen_ids.add(entry.id)

            results.append(
                VectorStoreResult(
                    entry=entry,
                    score=point.score,
                    vectors=(point.payload or {}).get("__embeddings", {}),
                )
            )

            if len(results) >= merged_options.k:
                break

        return results

    @traceable
    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.

        Raises:
            ValueError: If collection named `self._index_name` is not present in the vector store.
        """
        with contextlib.suppress(KeyError):  # it's ok if a point already doesn't exist
            await self._client.delete(
                collection_name=self._index_name,
                points_selector=models.PointIdsList(
                    points=[
                        str(self._internal_id(id, embedding_type))
                        for id in ids
                        for embedding_type in self._embedding_types
                    ],
                ),
            )

    @staticmethod
    def _create_qdrant_filter(where: WhereQuery) -> Filter:
        """
        Creates the QdrantFilter from the given WhereQuery.

        Args:
            where: The WhereQuery to filter.

        Returns:
            The created filter.
        """
        where = flatten_dict(where)  # type: ignore

        return Filter(
            must=[
                FieldCondition(key=f"metadata.{key}", match=MatchValue(value=cast(str | int | bool, value)))
                for key, value in where.items()
            ]
        )

    @traceable
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
                Reference: https://qdrant.tech/documentation/concepts/filtering
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        collection_exists = await self._client.collection_exists(collection_name=self._index_name)
        if not collection_exists:
            return []

        limit = limit or (await self._client.count(collection_name=self._index_name)).count

        qdrant_filter = self._create_qdrant_filter(where) if where else None

        results = await self._client.query_points(
            collection_name=self._index_name,
            query_filter=qdrant_filter,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )

        vs_results = [VectorStoreEntry.model_validate(point.payload) for point in results.points]
        deduplicated_results = list({r.id: r for r in vs_results}.values())

        return deduplicated_results
