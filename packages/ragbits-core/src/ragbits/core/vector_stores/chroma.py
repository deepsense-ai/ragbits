from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal

import chromadb
from chromadb import Collection
from chromadb.api import ClientAPI

from ragbits.core.metadata_store import get_metadata_store
from ragbits.core.metadata_store.base import MetadataStore
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery

CHROMA_IDS_KEY = "ids"
CHROMA_DOCUMENTS_KEY = "documents"
CHROMA_DISTANCES_KEY = "distances"
CHROMA_METADATA_KEY = "metadatas"
CHROMA_EMBEDDINGS_KEY = "embeddings"
CHROMA_LIST_INCLUDE_KEYS = [CHROMA_DOCUMENTS_KEY, CHROMA_METADATA_KEY, CHROMA_EMBEDDINGS_KEY]
CHROMA_QUERY_INCLUDE_KEYS = CHROMA_LIST_INCLUDE_KEYS + [CHROMA_DISTANCES_KEY]


class ChromaVectorStore(VectorStore):
    """
    Class that stores text embeddings using [Chroma](https://docs.trychroma.com/).
    """

    METADATA_INNER_KEY = "__metadata"

    def __init__(
        self,
        client: ClientAPI,
        index_name: str,
        distance_method: Literal["l2", "ip", "cosine"] = "l2",
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ):
        """
        Initializes the ChromaVectorStore with the given parameters.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use.
        """
        super().__init__(default_options, metadata_store)
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method
        self._collection = self._get_chroma_collection()

    def _get_chroma_collection(self) -> Collection:
        """
        Gets or creates a collection with the given name and metadata.

        Returns:
            The collection.
        """
        return self._client.get_or_create_collection(
            name=self._index_name,
            metadata={"hnsw:space": self._distance_method},
        )

    @classmethod
    def from_config(cls, config: dict) -> ChromaVectorStore:
        """
        Creates and returns an instance of the ChromaVectorStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the ChromaVectorStore instance.

        Returns:
            An initialized instance of the ChromaVectorStore class.
        """
        client = get_cls_from_config(config["client"]["type"], chromadb)  # type: ignore
        return cls(
            client=client(**config["client"].get("config", {})),
            index_name=config["index_name"],
            distance_method=config.get("distance_method", "l2"),
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=get_metadata_store(config.get("metadata_store_config", {})),
        )

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        # TODO: Think about better id components for hashing
        ids = [sha256(entry.key.encode("utf-8")).hexdigest() for entry in entries]
        embeddings = [entry.vector for entry in entries]

        if self._metadata_store is not None:
            for key, meta in zip(ids, [entry.metadata for entry in entries], strict=False):
                await self._metadata_store.store(key, meta)
            metadata_to_store = None
        else:
            metadata_to_store = [
                {self.METADATA_INNER_KEY: json.dumps(entry.metadata, default=str)} for entry in entries
            ]

        contents = [entry.key for entry in entries]
        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadata_to_store, documents=contents)  # type: ignore

    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
        options = self._default_options if options is None else options
        results = self._collection.query(
            query_embeddings=vector,
            n_results=options.k,
            include=CHROMA_QUERY_INCLUDE_KEYS,  # type: ignore
        )
        metadatas = results.get(CHROMA_METADATA_KEY) or []
        embeddings = results.get(CHROMA_EMBEDDINGS_KEY) or []
        distances = results.get(CHROMA_DISTANCES_KEY) or []
        ids = results.get(CHROMA_IDS_KEY) or []
        documents = results.get(CHROMA_DOCUMENTS_KEY) or []

        return [
            VectorStoreEntry(
                key=document,
                vector=list(embeddings),
                metadata=await self._load_sample_metadata(metadata, sample_id),
            )
            for batch in zip(metadatas, embeddings, distances, ids, documents, strict=False)  # type: ignore
            for metadata, embeddings, distance, sample_id, document in zip(*batch, strict=False)
            if options.max_distance is None or distance <= options.max_distance
        ]

    async def _load_sample_metadata(self, metadata: dict, sample_id: str) -> dict:
        if self._metadata_store is not None:
            metadata = await self._metadata_store.get(sample_id)
        else:
            metadata = json.loads(metadata[self.METADATA_INNER_KEY])

        return metadata

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
        # Cast `where` to chromadb's Where type
        where_chroma: chromadb.Where | None = dict(where) if where else None

        get_results = self._collection.get(
            where=where_chroma,
            limit=limit,
            offset=offset,
            include=CHROMA_LIST_INCLUDE_KEYS,  # type: ignore
        )
        metadatas = get_results.get(CHROMA_METADATA_KEY) or []
        embeddings = get_results.get(CHROMA_EMBEDDINGS_KEY) or []
        documents = get_results.get(CHROMA_DOCUMENTS_KEY) or []
        ids = get_results.get(CHROMA_IDS_KEY) or []

        return [
            VectorStoreEntry(
                key=document,
                vector=list(embedding),
                metadata=await self._load_sample_metadata(metadata, sample_id),
            )
            for metadata, embedding, sample_id, document in zip(metadatas, embeddings, ids, documents, strict=False)  # type: ignore
        ]
