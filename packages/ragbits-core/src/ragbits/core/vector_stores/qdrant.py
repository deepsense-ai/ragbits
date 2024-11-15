import json

import qdrant_client
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, Filter, VectorParams

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores import get_metadata_store
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions


class QdrantVectorStore(VectorStore):
    """
    Vector store implementation using [Qdrant](https://qdrant.tech).
    """

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
    def from_config(cls, config: dict) -> "QdrantVectorStore":
        """
        Creates and returns an instance of the QdrantVectorStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the QdrantVectorStore instance.

        Returns:
            An initialized instance of the QdrantVectorStore class.
        """
        client_cls = get_cls_from_config(config["client"]["type"], qdrant_client)
        return cls(
            client=client_cls(**config["client"].get("config", {})),
            index_name=config["index_name"],
            distance_method=config.get("distance_method", Distance.COSINE),
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=get_metadata_store(config.get("metadata_store")),
        )

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

        if not await self._client.collection_exists(self._index_name):
            await self._client.create_collection(
                collection_name=self._index_name,
                vectors_config=VectorParams(size=len(entries[0].vector), distance=self._distance_method),
            )

        ids = [entry.id for entry in entries]
        embeddings = [entry.vector for entry in entries]
        payloads = [{"document": entry.key} for entry in entries]
        metadatas = [entry.metadata for entry in entries]

        metadatas = (
            [{"metadata": json.dumps(metadata, default=str)} for metadata in metadatas]
            if self._metadata_store is None
            else await self._metadata_store.store(ids, metadatas)  # type: ignore
        )
        if metadatas is not None:
            payloads = [{**payload, **metadata} for (payload, metadata) in zip(payloads, metadatas, strict=True)]

        self._client.upload_collection(
            collection_name=self._index_name,
            vectors=embeddings,
            payload=payloads,
            ids=ids,
            wait=True,
        )

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the Qdrant collection based on vector similarity.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.

        Raises:
            MetadataNotFoundError: If metadata cannot be retrieved
        """
        options = options or self._default_options
        score_threshold = 1 - options.max_distance if options.max_distance else None

        results = await self._client.query_points(
            collection_name=self._index_name,
            query=vector,
            limit=options.k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=True,
        )

        ids = [point.id for point in results.points]
        vectors = [point.vector for point in results.points]
        documents = [point.payload["document"] for point in results.points]  # type: ignore
        metadatas = (
            [json.loads(point.payload["metadata"]) for point in results.points]  # type: ignore
            if self._metadata_store is None
            else await self._metadata_store.get(ids)  # type: ignore
        )

        return [
            VectorStoreEntry(
                id=str(id),
                key=document,
                vector=vector,  # type: ignore
                metadata=metadata,
            )
            for id, document, vector, metadata in zip(ids, documents, vectors, metadatas, strict=True)
        ]

    @traceable
    async def list(  # type: ignore
        self,
        where: Filter | None = None,  # type: ignore
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
        results = await self._client.query_points(
            collection_name=self._index_name,
            query_filter=where,
            limit=limit or 10,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )

        ids = [point.id for point in results.points]
        vectors = [point.vector for point in results.points]
        documents = [point.payload["document"] for point in results.points]  # type: ignore
        metadatas = (
            [json.loads(point.payload["metadata"]) for point in results.points]  # type: ignore
            if self._metadata_store is None
            else await self._metadata_store.get(ids)  # type: ignore
        )

        return [
            VectorStoreEntry(
                id=str(id),
                key=document,
                vector=vector,  # type: ignore
                metadata=metadata,
            )
            for id, document, vector, metadata in zip(ids, documents, vectors, metadatas, strict=True)
        ]
