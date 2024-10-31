from __future__ import annotations

import json
import uuid

import qdrant_client
from qdrant_client import AsyncQdrantClient, models

from ragbits.core.metadata_stores import get_metadata_store
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions

DOCUMENT_PAYLOAD_KEY = "__document"
METADATA_PAYLOAD_KEY = "__metadata"


class QdrantVectorStore(VectorStore):
    """
    Vectorstore implementation using [Qdrant](https://qdrant.tech/).
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        distance: models.Distance = models.Distance.COSINE,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new QdrantVectorStore instance.

        Args:
            client: An instance of the Qdrant client.
            collection_name: The name of the Qdrant collection.
            distance: The distance metric to use when creating the collection.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in Qdrant.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)
        self._client = client
        self._collection_name = collection_name
        self._distance = distance

    @classmethod
    def from_config(cls, config: dict) -> QdrantVectorStore:
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
            collection_name=config["collection_name"],
            distance=config.get("distance", "Cosine"),
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=get_metadata_store(config.get("metadata_store")),
        )

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores vector entries in the Qdrant collection.

        Args:
            entries: List of VectorStoreEntry objects to store

        Raises:
            ValueError: If entries list is empty
            QdrantException: If upload to collection fails
        """
        # Generate deterministic UUIDs for consistent addressing

        if not entries:
            raise ValueError("Empty list of entries are not allowed.")

        if not await self._client.collection_exists(self._collection_name):
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(size=len(entries[0].vector), distance=self._distance),
            )
        ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, str(entry))) for entry in entries]

        documents, embeddings, metadatas = zip(
            *[(entry.key, entry.vector, entry.metadata) for entry in entries], strict=True
        )

        if self._metadata_store is not None:
            await self._metadata_store.store(ids, metadatas)
            payloads = [{DOCUMENT_PAYLOAD_KEY: doc} for doc in documents]
        else:
            payloads = [
                {DOCUMENT_PAYLOAD_KEY: doc, METADATA_PAYLOAD_KEY: json.dumps(meta, default=str, ensure_ascii=False)}
                for doc, meta in zip(documents, metadatas, strict=True)
            ]

        self._client.upload_collection(
            collection_name=self._collection_name,
            vectors=list(embeddings),
            payload=list(payloads),
            ids=list(ids),
            wait=True,
        )

    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the Qdrant collection based on vector similarity.

        Args:
            vector: Query vector for similarity search
            options: Configuration options for the query (default: self._default_options)

        Returns:
            List[VectorStoreEntry]: Matched entries sorted by similarity

        Raises:
            ValueError: If vector dimensions don't match collection
            MetadataNotFoundError: If metadata cannot be retrieved
        """
        if not vector:
            raise ValueError("Query vector cannot be empty")

        # Use default options if none provided
        query_options = options or self._default_options

        score_threshold = 1 - query_options.max_distance if query_options.max_distance else None

        points = (
            await self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                limit=query_options.k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=True,
            )
        ).points

        return await self._parse_points(points)

    async def list(
        self,
        where: models.Filter | None = None,  # type: ignore
        limit: int | None = None,
        offset: int = 0,
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector store. The entries can be filtered, limited and offset.

        Args:
            where: Conditions for filtering results.
            Reference: https://qdrant.tech/documentation/concepts/filtering/
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        points = (
            await self._client.query_points(
                collection_name=self._collection_name,
                query_filter=where,
                limit=limit or 10,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
        ).points

        return await self._parse_points(points)

    async def _parse_points(self, points: list[models.ScoredPoint]) -> list[VectorStoreEntry]:  # type: ignore
        points_data = [(point.id, point.vector, point.payload) for point in points]  # type: ignore
        ids, vectors, payloads = zip(*points_data, strict=True)

        if self._metadata_store:
            metadatas = await self._metadata_store.get(*ids)
        else:
            metadatas = [json.loads(payload.get(METADATA_PAYLOAD_KEY, "{}")) for payload in payloads]

        documents = [payload.get(DOCUMENT_PAYLOAD_KEY, "") for payload in payloads]

        return [
            VectorStoreEntry(
                key=document,
                vector=vector,
                metadata=metadata,
            )
            for document, vector, metadata in zip(documents, vectors, metadatas, strict=True)
        ]
