from typing import Literal

import chromadb
from chromadb.api import ClientAPI
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict, unflatten_dict
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery


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
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in ChromaDB.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)
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

        ids = [entry.id for entry in entries]
        documents = [entry.key for entry in entries]
        embeddings = [entry.vector for entry in entries]
        metadatas = [entry.metadata for entry in entries]

        # Flatten metadata
        flattened_metadatas = [self._flatten_metadata(metadata) for metadata in metadatas]

        metadatas = (
            flattened_metadatas
            if self._metadata_store is None
            else await self._metadata_store.store(ids, flattened_metadatas)  # type: ignore
        )

        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)  # type: ignore

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        results = self._collection.query(
            query_embeddings=vector,
            n_results=merged_options.k,
            include=["metadatas", "embeddings", "distances", "documents"],
        )

        ids = results.get("ids") or []
        embeddings = results.get("embeddings") or []
        distances = results.get("distances") or []
        documents = results.get("documents") or []
        metadatas = [
            [metadata for batch in results.get("metadatas", []) for metadata in batch]  # type: ignore
            if self._metadata_store is None
            else await self._metadata_store.get(*ids)
        ]

        return [
            VectorStoreEntry(
                id=id,
                key=document,
                vector=list(embeddings),
                metadata=unflatten_dict(metadata) if metadata else {},  # type: ignore
            )
            for batch in zip(ids, metadatas, embeddings, distances, documents, strict=True)
            for id, metadata, embeddings, distance, document in zip(*batch, strict=True)
            if merged_options.max_distance is None or distance <= merged_options.max_distance
        ]

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        self._collection.delete(ids=ids)

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
        embeddings = results.get("embeddings") or []
        documents = results.get("documents") or []
        metadatas = (
            results.get("metadatas") or [] if self._metadata_store is None else await self._metadata_store.get(ids)
        )

        return [
            VectorStoreEntry(
                id=id,
                key=document,
                vector=list(embedding),
                metadata=unflatten_dict(metadata) if metadata else {},  # type: ignore
            )
            for id, metadata, embedding, document in zip(ids, metadatas, embeddings, documents, strict=True)
        ]

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flattens the metadata dictionary. Removes any None values as they are not supported by ChromaDB."""
        return {k: v for k, v in flatten_dict(metadata).items() if v is not None}
