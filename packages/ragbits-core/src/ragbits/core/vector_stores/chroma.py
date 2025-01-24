from typing import Literal

import chromadb
from chromadb.api import ClientAPI
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict
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
        metadatas = [entry.metadata for entry in entries]

        # Flatten metadata
        flattened_metadatas = [flatten_dict(metadata) for metadata in metadatas]

        metadatas = (
            flattened_metadatas
            if self._metadata_store is None
            else await self._metadata_store.store(ids, flattened_metadatas)  # type: ignore
        )

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
            collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": self._distance_method},
            )
            collection.add(
                ids=[id for id, _ in group],
                embeddings=[vector for _, vector in group],
                metadatas=metadatas,  # type: ignore
                documents=documents,
            )

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreResult]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The entries with their scores.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        # Query each embedding type collection
        collections = self._client.list_collections()
        results = []
        for collection in collections:
            if not collection.name.startswith(self._index_name):
                continue

            embedding_type = collection.name[len(self._index_name) + 1 :]
            query_results = collection.query(
                query_embeddings=[vector],
                n_results=merged_options.k,
                include=["metadatas", "documents", "distances", "embeddings"],
            )

            for i, (id, metadata, document, distance, embedding) in enumerate(
                zip(
                    query_results["ids"][0],
                    query_results["metadatas"][0],
                    query_results["documents"][0],
                    query_results["distances"][0],
                    query_results["embeddings"][0],
                    strict=True,
                )
            ):
                if merged_options.max_distance is not None and distance > merged_options.max_distance:
                    continue

                entry = VectorStoreEntry(
                    id=id,
                    key=document,
                    metadata=metadata,
                )
                results.append(
                    VectorStoreResult(
                        entry=entry,
                        vectors={embedding_type: embedding},
                        score=distance,
                    )
                )

        # Sort by score and return top k
        results.sort(key=lambda x: x.score or float("inf"))
        return results[: merged_options.k]

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        collections = self._client.list_collections()
        for collection in collections:
            if not collection.name.startswith(self._index_name):
                continue
            collection.delete(ids=ids)

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
        # Get entries from the first collection (they should be the same in all collections)
        collections = self._client.list_collections()
        for collection in collections:
            if not collection.name.startswith(self._index_name):
                continue

            where_clause = where if where else {}
            results = collection.get(
                where=where_clause,  # type: ignore
                limit=limit,
                offset=offset,
                include=["metadatas", "documents"],
            )

            return [
                VectorStoreEntry(
                    id=id,
                    key=document,
                    metadata=metadata,
                )
                for id, document, metadata in zip(
                    results["ids"],
                    results["documents"],
                    results["metadatas"],
                    strict=True,
                )
            ]

        return []
