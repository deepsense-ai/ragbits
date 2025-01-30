from typing import Literal

import chromadb
from chromadb.api import ClientAPI
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.embeddings import Embeddings, EmbeddingType
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict, unflatten_dict
from ragbits.core.vector_stores.base import (
    VectorStore,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    WhereQuery,
)


class ChromaVectorStore(VectorStore[VectorStoreOptions]):
    """
    Vector store implementation using [Chroma](https://docs.trychroma.com).
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: ClientAPI,
        index_name: str,
        distance_method: Literal["l2", "ip", "cosine"] = "cosine",
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
        default_embedder: Embeddings | None = None,
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in ChromaDB.
            default_embedder: The default embedder to use for converting entries to vectors.
        """
        super().__init__(
            default_options=default_options, metadata_store=metadata_store, default_embedder=default_embedder
        )
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method
        self._collection = self._client.get_or_create_collection(
            name=self._index_name,
            metadata={"hnsw:space": self._distance_method},
        )

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
        client_cls = import_by_path(client_options.type, chromadb)
        config["client"] = client_cls(**client_options.config)
        return super().from_config(config)

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        if not entries:
            return

        if not self._default_embedder:
            raise ValueError("No default embedder provided for ChromaVectorStore")

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
                metadatas.append(self._flatten_metadata(entry.metadata))

            if entry.image_bytes is not None and self._default_embedder.image_support():
                image_vectors = await self._default_embedder.embed_image([entry.image_bytes])
                ids.append(f"{entry.id}_image")
                documents.append(entry.text or "")  # Use text if available, empty string if not
                embeddings.append(image_vectors[0])
                metadata = self._flatten_metadata(entry.metadata)
                metadata["embedding_type"] = str(EmbeddingType.IMAGE)
                metadatas.append(metadata)

        if not ids:
            return

        if self._metadata_store is not None:
            metadatas = await self._metadata_store.store(ids, metadatas)  # type: ignore

        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)  # type: ignore

    @traceable
    async def retrieve(
        self, query: VectorStoreEntry, options: VectorStoreOptions | None = None
    ) -> list[VectorStoreResult]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            query: The query entry to search for.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        if not self._default_embedder:
            raise ValueError("No default embedder provided for ChromaVectorStore")

        merged_options = (self.default_options | options) if options else self.default_options
        query_vectors = []

        if query.text is not None:
            text_vectors = await self._default_embedder.embed_text([query.text])
            query_vectors.append(text_vectors[0])

        if query.image_bytes is not None and self._default_embedder.image_support():
            image_vectors = await self._default_embedder.embed_image([query.image_bytes])
            query_vectors.append(image_vectors[0])

        if not query_vectors:
            return []

        results = []
        for query_vector in query_vectors:
            chroma_results = self._collection.query(
                query_embeddings=query_vector,
                n_results=merged_options.k,
                include=["metadatas", "embeddings", "distances", "documents"],
            )

            ids = chroma_results.get("ids") or []
            embeddings = chroma_results.get("embeddings") or []
            distances = chroma_results.get("distances") or []
            documents = chroma_results.get("documents") or []
            metadatas = [
                [metadata for batch in chroma_results.get("metadatas", []) for metadata in batch]  # type: ignore
                if self._metadata_store is None
                else await self._metadata_store.get(*ids)
            ]

            for batch in zip(ids, metadatas, embeddings, distances, documents, strict=True):
                for id, metadata, embedding, distance, document in zip(*batch, strict=True):
                    if merged_options.max_distance is None or distance <= merged_options.max_distance:
                        # Remove image suffix if present
                        original_id = id[:-6] if id.endswith("_image") else id

                        # Create entry
                        entry = VectorStoreEntry(
                            id=original_id,
                            key=document,
                            text=document if not id.endswith("_image") else None,
                            metadata=unflatten_dict(metadata) if metadata else {},  # type: ignore
                        )

                        # Create vectors map
                        vectors = {}
                        embedding_type = metadata.get("embedding_type", str(EmbeddingType.TEXT))
                        vectors[embedding_type] = list(embedding)

                        results.append(VectorStoreResult(entry=entry, vectors=vectors, score=1.0 - distance))

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
        self._collection.delete(ids=all_ids)

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

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        # Cast `where` to chromadb's Where type
        where_chroma: chromadb.Where | None = dict(where) if where else None

        results = self._collection.get(
            where=where_chroma,
            limit=limit,
            offset=offset,
            include=["metadatas", "embeddings", "documents"],
        )

        ids = results.get("ids") or []
        documents = results.get("documents") or []
        metadatas = (
            results.get("metadatas") or [] if self._metadata_store is None else await self._metadata_store.get(ids)
        )

        # Group entries by original id (removing _image suffix)
        entries_map = {}
        for id, metadata, document in zip(ids, metadatas, documents, strict=True):
            original_id = id[:-6] if id.endswith("_image") else id
            if original_id not in entries_map:
                entries_map[original_id] = VectorStoreEntry(
                    id=original_id,
                    key=document,
                    text=document if not id.endswith("_image") else None,
                    metadata=unflatten_dict(metadata) if metadata else {},  # type: ignore
                )

        return list(entries_map.values())

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flattens the metadata dictionary. Removes any None values as they are not supported by ChromaDB."""
        return {k: v for k, v in flatten_dict(metadata).items() if v is not None}
