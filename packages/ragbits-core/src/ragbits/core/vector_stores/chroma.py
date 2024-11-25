from typing import Literal

import chromadb
from chromadb.api import ClientAPI

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores import get_metadata_store
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.utils.dict_transformations import flatten_dict, unflatten_dict
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery


class ChromaVectorStore(VectorStore):
    """
    Vector store implementation using [Chroma](https://docs.trychroma.com).
    """

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
    def from_config(cls, config: dict) -> "ChromaVectorStore":
        """
        Creates and returns an instance of the ChromaVectorStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the ChromaVectorStore instance.

        Returns:
            An initialized instance of the ChromaVectorStore class.
        """
        client_cls = get_cls_from_config(config["client"]["type"], chromadb)
        return cls(
            client=client_cls(**config["client"].get("config", {})),
            index_name=config["index_name"],
            distance_method=config.get("distance_method", "cosine"),
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=get_metadata_store(config.get("metadata_store")),
        )

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
        flattened_metadatas = [flatten_dict(metadata) for metadata in metadatas]

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
        options = self._default_options if options is None else options

        results = self._collection.query(
            query_embeddings=vector,
            n_results=options.k,
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
            if options.max_distance is None or distance <= options.max_distance
        ]

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
