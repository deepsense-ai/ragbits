import asyncio
from collections.abc import Callable, Coroutine, Iterable, Mapping
from typing import Any, cast
from uuid import UUID

import httpx
import qdrant_client
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams
from typing_extensions import Self

from ragbits.core.audit import trace, traceable
from ragbits.core.embeddings.base import Embedder
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict
from ragbits.core.vector_stores.base import (
    VectorStoreEntry,
    VectorStoreNeedingEmbedder,
    VectorStoreOptions,
    VectorStoreOptionsT,
    VectorStoreResult,
    WhereQuery,
)


class QdrantVectorStore(VectorStoreNeedingEmbedder[VectorStoreOptions]):
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

    def __reduce__(self) -> tuple[Callable, tuple]:
        """
        Enables the QdrantVectorStore to be pickled and unpickled.

        Returns:
            The tuple of function and its arguments that allows reconstruction of the QdrantVectorStore.
        """

        def _reconstruct(
            client_params: dict,
            index_name: str,
            embedder: Embedder,
            distance_method: Distance,
            default_options: VectorStoreOptions,
            embedding_name_text: str,
            embedding_name_image: str,
        ) -> QdrantVectorStore:
            return QdrantVectorStore(
                client=AsyncQdrantClient(**client_params),
                index_name=index_name,
                embedder=embedder,
                distance_method=distance_method,
                default_options=default_options,
                embedding_name_text=embedding_name_text,
                embedding_name_image=embedding_name_image,
            )

        return (
            _reconstruct,
            (
                self._client._init_options,
                self._index_name,
                self._embedder,
                self._distance_method,
                self.default_options,
                self._embedding_name_text,
                self._embedding_name_image,
            ),
        )

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

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores vector entries in the Qdrant collection.

        Args:
            entries: List of VectorStoreEntry objects to store

        Raises:
            QdrantException: If upload to collection fails.
        """
        with trace(
            entries=entries,
            index_name=self._index_name,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
            embedder_for_text=self._embedding_name_text,
            embedder_for_image=self._embedding_name_image,
        ):
            if not entries:
                return

            embeddings: dict = await self._create_embeddings(entries)

            if not await self._client.collection_exists(self._index_name):
                vector_size = self._detect_vector_size(embeddings.values())
                await self._client.create_collection(
                    collection_name=self._index_name,
                    vectors_config={
                        name: VectorParams(size=vector_size, distance=self._distance_method)
                        for name in [self._embedding_name_text, self._embedding_name_image]
                    },
                )

            points = (
                models.PointStruct(
                    id=str(entry.id),
                    vector=embeddings[entry.id],
                    payload=entry.model_dump(exclude_none=True),
                )
                for entry in entries
                if entry.id in embeddings
            )

            self._client.upload_points(
                collection_name=self._index_name,
                points=points,
                wait=True,
            )

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
        with trace(
            text=text,
            image=image,
            options=merged_options,
            index_name=self._index_name,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
            embedder_for_text=self._embedding_name_text,
            embedder_for_image=self._embedding_name_image,
        ) as outputs:
            vector_coroutines: list[Coroutine[Any, Any, list[list[float]]]] = []
            if text:
                vector_coroutines.append(self._embedder.embed_text([text]))
            if image:
                vector_coroutines.append(self._embedder.embed_image([image]))

            if not vector_coroutines:
                raise ValueError("Either text or image should be provided.")

            query_vectors = await asyncio.gather(*vector_coroutines)

            # TODO: Come up with a better way to query both image and text vectors
            # FusionQuery boosts entries that appear in both lists, i.e. those
            # that contain both text and image, which is probably not what we want.
            query_results = await self._client.query_points(
                prefetch=[
                    models.Prefetch(
                        query=vector[0],
                        using=name,
                    )
                    for vector in query_vectors
                    for name in [self._embedding_name_text, self._embedding_name_image]
                ],
                collection_name=self._index_name,
                query=models.FusionQuery(fusion=models.Fusion.DBSF),
                limit=merged_options.k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=True,
            )

            results: list[VectorStoreResult] = []

            for point in query_results.points:
                if not isinstance(point.vector, dict):
                    raise ValueError(f"For payload {point.payload}, vector is not a dict: {point.vector}")
                vector: dict = point.vector
                results.append(
                    VectorStoreResult(
                        entry=VectorStoreEntry.model_validate(point.payload),
                        score=point.score,
                        vectors=vector,
                    )
                )
            outputs.retrieved_entries = results
            return results

    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.

        Raises:
            ValueError: If collection named `self._index_name` is not present in the vector store.
        """
        with trace(ids=ids, index_name=self._index_name):
            await self._client.delete(
                collection_name=self._index_name,
                points_selector=models.PointIdsList(
                    points=[str(id) for id in ids],
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
        with trace(where=where, index_name=self._index_name, limit=limit, offset=offset) as outputs:
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
            outputs.listed_entries = [VectorStoreEntry.model_validate(point.payload) for point in results.points]
            return outputs.listed_entries
