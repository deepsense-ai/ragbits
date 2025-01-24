import json
import typing

import httpx
import qdrant_client
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, Filter, VectorParams
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, VectorStoreResult


class QdrantVectorStore(VectorStore[VectorStoreOptions]):
    """
    Vector store implementation using [Qdrant](https://qdrant.tech).
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: AsyncQdrantClient,
        index_name: str,
        distance_method: Distance = Distance.COSINE,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new QdrantVectorStore instance.

        Args:
            client: An instance of the Qdrant client.
            index_name: The name of the index.
            distance_method: The distance metric to use when creating the collection.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in Qdrant.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)
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

        Raises:
            ValidationError: The client or metadata_store configuration doesn't follow the expected format.
            InvalidConfigError: The client or metadata_store class can't be found or is not the correct type.
        """
        client_options = ObjectContructionConfig.model_validate(config["client"])
        client_cls = import_by_path(client_options.type, qdrant_client)
        if "limits" in client_options.config:
            limits = httpx.Limits(**client_options.config["limits"])
            client_options.config["limits"] = limits
        config["client"] = client_cls(**client_options.config)
        return super().from_config(config)

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

        # Group entries by embedding type
        embedding_groups: dict[str, list[tuple[str, list[float]]]] = {}
        for entry in entries:
            if "embedding_type" not in entry.metadata:
                raise ValueError("Entry must have embedding_type in metadata")
            embedding_type = entry.metadata["embedding_type"]
            vector = entry.metadata.pop("vector")
            if embedding_type not in embedding_groups:
                embedding_groups[embedding_type] = []
            embedding_groups[embedding_type].append((entry.id, vector))

        # Store each embedding type in a separate collection
        for embedding_type, group in embedding_groups.items():
            collection_name = f"{self._index_name}_{embedding_type}"
            if not await self._client.collection_exists(collection_name):
                await self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=len(group[0][1]), distance=self._distance_method),
                )

            ids = [id for id, _ in group]
            embeddings = [vector for _, vector in group]
            payloads = [{"document": entry.key} for entry in entries]
            metadatas = [entry.metadata for entry in entries]

            metadatas = (
                [{"metadata": json.dumps(metadata, default=str)} for metadata in metadatas]
                if self._metadata_store is None
                else await self._metadata_store.store(ids, metadatas)  # type: ignore
            )
            if metadatas is not None:
                payloads = [{**payload, **metadata} for (payload, metadata) in zip(payloads, metadatas, strict=True)]

            await self._client.upload_points(
                collection_name=collection_name,
                points=models.Batch(
                    ids=typing.cast(list[str | int], ids),
                    vectors=embeddings,
                    payloads=payloads,
                ),
                wait=True,
            )

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreResult]:
        """
        Retrieves entries from the Qdrant collection based on vector similarity.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The entries with their scores.

        Raises:
            MetadataNotFoundError: If metadata cannot be retrieved
        """
        merged_options = (self.default_options | options) if options else self.default_options
        score_threshold = 1 - merged_options.max_distance if merged_options.max_distance else None

        # Query each embedding type collection
        collections = await self._client.get_collections()
        results = []
        for collection in collections.collections:
            if not collection.name.startswith(self._index_name):
                continue

            embedding_type = collection.name[len(self._index_name) + 1:]
            query_results = await self._client.search(
                collection_name=collection.name,
                query_vector=vector,
                limit=merged_options.k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=True,
            )

            for point in query_results:
                metadata = json.loads(point.payload["metadata"]) if self._metadata_store is None else point.payload
                entry = VectorStoreEntry(
                    id=str(point.id),
                    key=point.payload["document"],
                    metadata=metadata,
                )
                results.append(
                    VectorStoreResult(
                        entry=entry,
                        vectors={embedding_type: point.vector},  # type: ignore
                        score=point.score,
                    )
                )

        # Sort by score and return top k
        results.sort(key=lambda x: x.score or float("inf"))
        return results[:merged_options.k]

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.

        Raises:
            ValueError: If collection named `self._index_name` is not present in the vector store.
        """
        collections = await self._client.get_collections()
        for collection in collections.collections:
            if not collection.name.startswith(self._index_name):
                continue
            await self._client.delete(
                collection_name=collection.name,
                points_selector=models.PointIdsList(
                    points=typing.cast(list[int | str], ids),
                ),
            )

    @traceable
    async def list(
        self, where: Filter | None = None, limit: int | None = None, offset: int = 0
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
        # Get entries from the first collection (they should be the same in all collections)
        collections = await self._client.get_collections()
        for collection in collections.collections:
            if not collection.name.startswith(self._index_name):
                continue

            collection_exists = await self._client.collection_exists(collection_name=collection.name)
            if not collection_exists:
                return []

            limit = limit or (await self._client.count(collection_name=collection.name)).count

            results = await self._client.scroll(
                collection_name=collection.name,
                limit=limit,
                offset=offset,
                with_payload=True,
                filter=where,
            )

            points = results[0]
            return [
                VectorStoreEntry(
                    id=str(point.id),
                    key=point.payload["document"],
                    metadata=json.loads(point.payload["metadata"])
                    if self._metadata_store is None
                    else point.payload,
                )
                for point in points
            ]

        return []
