from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal

try:
    import chromadb
    from chromadb import Collection
    from chromadb.api import ClientAPI
except ImportError:
    HAS_CHROMADB = False
else:
    HAS_CHROMADB = True

from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_store.base import VectorDBEntry, VectorStore, VectorStoreOptions, WhereQuery


class ChromaDBStore(VectorStore):
    """
    Class that stores text embeddings using [Chroma](https://docs.trychroma.com/).
    """

    def __init__(
        self,
        client: ClientAPI,
        index_name: str,
        distance_method: Literal["l2", "ip", "cosine"] = "l2",
        default_options: VectorStoreOptions | None = None,
    ):
        """
        Initializes the ChromaDBStore with the given parameters.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
        """
        if not HAS_CHROMADB:
            raise ImportError("Install the 'ragbits-document-search[chromadb]' extra to use LiteLLM embeddings models")

        super().__init__(default_options)
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
    def from_config(cls, config: dict) -> ChromaDBStore:
        """
        Creates and returns an instance of the ChromaDBStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the ChromaDBStore instance.

        Returns:
            An initialized instance of the ChromaDBStore class.
        """
        client = get_cls_from_config(config["client"]["type"], chromadb)  # type: ignore
        return cls(
            client=client(**config["client"].get("config", {})),
            index_name=config["index_name"],
            distance_method=config.get("distance_method", "l2"),
            default_options=VectorStoreOptions(**config.get("options", {})),
        )

    async def store(self, entries: list[VectorDBEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        # TODO: Think about better id components for hashing
        ids = [sha256(entry.key.encode("utf-8")).hexdigest() for entry in entries]
        embeddings = [entry.vector for entry in entries]
        metadatas = [
            {
                "__key": entry.key,
                "__metadata": json.dumps(entry.metadata, default=str),
            }
            for entry in entries
        ]
        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)  # type: ignore

    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorDBEntry]:
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
            include=["metadatas", "embeddings", "distances"],
        )
        metadatas = results.get("metadatas") or []
        embeddings = results.get("embeddings") or []
        distances = results.get("distances") or []

        return [
            VectorDBEntry(
                key=str(metadata["__key"]), vector=list(embeddings), metadata=json.loads(str(metadata["__metadata"]))
            )
            for batch in zip(metadatas, embeddings, distances, strict=False)
            for metadata, embeddings, distance in zip(*batch, strict=False)
            if options.max_distance is None or distance <= options.max_distance
        ]

    async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> list[VectorDBEntry]:
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
            include=["metadatas", "embeddings"],
        )
        metadatas = get_results.get("metadatas") or []
        embeddings = get_results.get("embeddings") or []

        return [
            VectorDBEntry(
                key=str(metadata["__key"]),
                vector=list(embedding),
                metadata=json.loads(str(metadata["__metadata"])),
            )
            for metadata, embedding in zip(metadatas, embeddings, strict=False)
        ]
