import json

import httpx
import qdrant_client
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.embeddings import Embeddings, EmbeddingType
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.vector_stores.base import (
    VectorStore,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    WhereQuery,
)


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
        default_embedder: Embeddings | None = None,
    ) -> None:
        """
        Constructs a new QdrantVectorStore instance.

        Args:
            client: An instance of the Qdrant client.
            index_name: The name of the index.
            distance_method: The distance metric to use when creating the collection.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in Qdrant.
            default_embedder: The default embedder to use for converting entries to vectors.
        """
        super().__init__(
            default_options=default_options, metadata_store=metadata_store, default_embedder=default_embedder
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

        if not self._default_embedder:
            raise ValueError("No default embedder provided for QdrantVectorStore")

        # Process entries and create points
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for entry in entries:
            if entry.text is not None:
                text_vectors = await self._default_embedder.embed_text([entry.text])
                ids.append(entry.id)
                documents.append(entry.text)
                embeddings.append(text_vectors[0])
                metadata = {"document": entry.text, "embedding_type": str(EmbeddingType.TEXT)}
                if entry.metadata:
                    metadata["metadata"] = json.dumps(entry.metadata, default=str)
                metadatas.append(metadata)

            if entry.image_bytes is not None and self._default_embedder.image_support():
                image_vectors = await self._default_embedder.embed_image([entry.image_bytes])
                ids.append(f"{entry.id}_image")
                documents.append(entry.text or "")  # Use text if available, empty string if not
                embeddings.append(image_vectors[0])
                metadata = {"document": entry.text or "", "embedding_type": str(EmbeddingType.IMAGE)}
                if entry.metadata:
                    metadata["metadata"] = json.dumps(entry.metadata, default=str)
                metadatas.append(metadata)

        if not ids:
            return

        # Create collection if it doesn't exist
        if not await self._client.collection_exists(self._index_name):
            await self._client.create_collection(
                collection_name=self._index_name,
                vectors_config=VectorParams(size=len(embeddings[0]), distance=self._distance_method),
            )

        # Store metadata if using external metadata store
        if self._metadata_store is not None:
            metadatas = await self._metadata_store.store(ids, metadatas)  # type: ignore

        # Upload points to collection
        self._client.upload_collection(
            collection_name=self._index_name,
            vectors=embeddings,
            payload=metadatas,
            ids=ids,
            wait=True,
        )

    @traceable
    async def retrieve(
        self, query: VectorStoreEntry, options: VectorStoreOptions | None = None
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store.

        Args:
            query: The query entry to search for.
            options: The options for querying the vector store.

        Returns:
            The results, containing entries, their vectors and similarity scores.
        """
        if not self._default_embedder:
            raise ValueError("No default embedder provided for QdrantVectorStore")

        merged_options = (self.default_options | options) if options else self.default_options
        query_vectors = []

        if query.text is not None:
            text_vectors = await self._default_embedder.embed_text([query.text])
            query_vectors.append((text_vectors[0], EmbeddingType.TEXT))

        if query.image_bytes is not None and self._default_embedder.image_support():
            image_vectors = await self._default_embedder.embed_image([query.image_bytes])
            query_vectors.append((image_vectors[0], EmbeddingType.IMAGE))

        if not query_vectors:
            return []

        results = []
        for query_vector, _embedding_type in query_vectors:
            search_results = await self._client.search(
                collection_name=self._index_name,
                query_vector=query_vector,
                limit=merged_options.k,
                score_threshold=merged_options.max_distance,
                with_vectors=True,
            )

            for result in search_results:
                if result.payload is None:
                    continue

                # Get metadata from store or payload
                metadata = {}
                if self._metadata_store is not None:
                    metadata = (await self._metadata_store.get([str(result.id)]))[0]
                elif "metadata" in result.payload:
                    metadata = json.loads(result.payload["metadata"])

                # Remove image suffix if present
                original_id = str(result.id)
                if original_id.endswith("_image"):
                    original_id = original_id[:-6]

                # Create entry
                entry = VectorStoreEntry(
                    id=original_id,
                    key=result.payload.get("document", ""),
                    text=result.payload.get("document") if not str(result.id).endswith("_image") else None,
                    metadata=metadata,
                )

                # Create vectors map
                vectors = {}
                result_embedding_type = result.payload.get("embedding_type", str(EmbeddingType.TEXT))
                vectors[result_embedding_type] = result.vector

                results.append(VectorStoreResult(entry=entry, vectors=vectors, score=result.score))

        # Deduplicate results by entry id, keeping the highest score
        unique_results = {}
        for result in results:
            if result.entry.id not in unique_results or result.score > unique_results[result.entry.id].score:
                unique_results[result.entry.id] = result

        return list(unique_results.values())

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        # Also remove image entries if they exist
        all_ids = []
        for id in ids:
            all_ids.append(id)
            all_ids.append(f"{id}_image")
        await self._client.delete(
            collection_name=self._index_name,
            points_selector=all_ids,
        )

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
        # Convert where dict to Qdrant filter
        filter_conditions = None
        if where:
            filter_conditions = {"must": [{"key": key, "match": {"value": value}} for key, value in where.items()]}

        # Get points from collection
        results = await self._client.scroll(
            collection_name=self._index_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            filter=filter_conditions,
        )

        if not results.points:
            return []

        # Group entries by original id (removing _image suffix)
        entries_map = {}
        for point in results.points:
            if point.payload is None:
                continue

            # Get metadata from store or payload
            metadata = {}
            if self._metadata_store is not None:
                metadata = (await self._metadata_store.get([str(point.id)]))[0]
            elif "metadata" in point.payload:
                metadata = json.loads(point.payload["metadata"])

            # Remove image suffix if present
            original_id = str(point.id)
            if original_id.endswith("_image"):
                original_id = original_id[:-6]

            if original_id not in entries_map:
                entries_map[original_id] = VectorStoreEntry(
                    id=original_id,
                    key=point.payload.get("document", ""),
                    text=point.payload.get("document") if not str(point.id).endswith("_image") else None,
                    metadata=metadata,
                )

        return list(entries_map.values())
