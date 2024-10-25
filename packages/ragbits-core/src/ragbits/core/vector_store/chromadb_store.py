from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal

try:
    import chromadb

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

from ragbits.core.embeddings import Embeddings
from ragbits.core.metadata_store.base import MetadataStore
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_store import VectorDBEntry, VectorStore, WhereQuery

CHROMA_IDS_KEY = "ids"
CHROMA_DOCUMENTS_KEY = "documents"
CHROMA_DISTANCES_KEY = "distances"
CHROMA_METADATA_KEY = "metadatas"
CHROMA_EMBEDDINGS_KEY = "embeddings"
CHROMA_INCLUDE_KEYS = [CHROMA_DOCUMENTS_KEY, CHROMA_DISTANCES_KEY, CHROMA_METADATA_KEY, CHROMA_EMBEDDINGS_KEY]


class ChromaDBStore(VectorStore):
    """
    Class that stores text embeddings using [Chroma](https://docs.trychroma.com/).
    """

    DEFAULT_DISTANCE_METHOD = "l2"
    METADATA_INNER_KEY = "__metadata"

    def __init__(
        self,
        index_name: str,
        chroma_client: chromadb.ClientAPI,
        embedding_function: Embeddings | chromadb.EmbeddingFunction,
        max_distance: float | None = None,
        distance_method: Literal["l2", "ip", "cosine"] = "l2",
        metadata_store: MetadataStore | None = None,
    ):
        """
        Initializes the ChromaDBStore with the given parameters.

        Args:
            index_name: The name of the index.
            chroma_client: The ChromaDB client.
            embedding_function: The embedding function.
            max_distance: The maximum distance for similarity.
            distance_method: The distance method to use.
            metadata_store: The metadata store to use.
        """
        if not HAS_CHROMADB:
            raise ImportError("Install the 'ragbits-document-search[chromadb]' extra to use LiteLLM embeddings models")

        super().__init__(metadata_store)
        self._index_name = index_name
        self._chroma_client = chroma_client
        self._embedding_function = embedding_function
        self._max_distance = max_distance
        self._metadata = {"hnsw:space": distance_method}
        self._collection: chromadb.Collection | None = None

    @classmethod
    def from_config(cls, config: dict) -> ChromaDBStore:
        """
        Creates and returns an instance of the ChromaDBStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the ChromaDBStore instance.

        Returns:
            An initialized instance of the ChromaDBStore class.
        """
        chroma_client = get_cls_from_config(config["chroma_client"]["type"], chromadb)(
            **config["chroma_client"].get("config", {})
        )
        embedding_function = get_cls_from_config(config["embedding_function"]["type"], chromadb)(
            **config["embedding_function"].get("config", {})
        )

        return cls(
            config["index_name"],
            chroma_client,
            embedding_function,
            max_distance=config.get("max_distance"),
            distance_method=config.get("distance_method", cls.DEFAULT_DISTANCE_METHOD),
        )

    async def _get_chroma_collection(self) -> chromadb.Collection:
        """
        Based on the selected embedding_function, chooses how to retrieve the ChromaDB collection.
        If the collection doesn't exist, it creates one.

        Returns:
            Retrieved collection
        """
        if self._collection is not None:
            return self._collection

        if self.metadata_store is not None:
            await self.metadata_store.store_global(self._metadata)
            metadata_to_store = None
        else:
            metadata_to_store = self._metadata
        if isinstance(self._embedding_function, Embeddings):
            return self._chroma_client.get_or_create_collection(name=self._index_name, metadata=metadata_to_store)

        self._collection = self._chroma_client.get_or_create_collection(
            name=self._index_name,
            metadata=metadata_to_store,
            embedding_function=self._embedding_function,
        )
        return self._collection

    def _return_best_match(self, retrieved: dict) -> str | None:
        """
        Based on the retrieved data, returns the best match or None if no match is found.

        Args:
            retrieved: Retrieved data, with a column-first format.

        Returns:
            The best match or None if no match is found.
        """
        if self._max_distance is None or retrieved[CHROMA_DISTANCES_KEY][0][0] <= self._max_distance:
            return retrieved[CHROMA_DOCUMENTS_KEY][0][0]

        return None

    @staticmethod
    def _process_db_entry(entry: VectorDBEntry) -> tuple[str, list[float], str, dict]:
        doc_id = sha256(entry.key.encode("utf-8")).hexdigest()
        embedding = entry.vector

        return doc_id, embedding, entry.key, entry.metadata

    @property
    def embedding_function(self) -> Embeddings | chromadb.EmbeddingFunction:
        """
        Returns the embedding function.

        Returns:
            The embedding function.
        """
        return self._embedding_function

    async def store(self, entries: list[VectorDBEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        entries_processed = list(map(self._process_db_entry, entries))
        ids, embeddings, contents, metadatas = map(list, zip(*entries_processed, strict=False))

        if self.metadata_store is not None:
            for key, meta in zip(ids, metadatas, strict=False):
                await self.metadata_store.store(key, meta)
            metadata_to_store = None
        else:
            metadata_to_store = [{self.METADATA_INNER_KEY: json.dumps(m, default=str)} for m in metadatas]

        collection = await self._get_chroma_collection()
        collection.add(ids=ids, embeddings=embeddings, metadatas=metadata_to_store, documents=contents)  # type: ignore

    async def _extract_entries_from_query(
        self, query_results: chromadb.api.types.QueryResult | chromadb.api.types.GetResult
    ) -> list[VectorDBEntry]:
        db_entries: list[VectorDBEntry] = []

        if len(query_results[CHROMA_DOCUMENTS_KEY]) < 1:  # type: ignore
            return db_entries
        for i in range(len(query_results[CHROMA_DOCUMENTS_KEY][0])):  # type: ignore
            key = query_results[CHROMA_DOCUMENTS_KEY][0][i]  # type: ignore
            if self.metadata_store is not None:
                metadata = await self.metadata_store.get(query_results[CHROMA_IDS_KEY][0][i])  # type: ignore
            else:
                metadata = json.loads(query_results[CHROMA_METADATA_KEY][0][i][self.METADATA_INNER_KEY])  # type: ignore

            db_entry = VectorDBEntry(
                key=key,
                vector=query_results[CHROMA_EMBEDDINGS_KEY][0][i],  # type: ignore
                metadata=metadata,
            )
            db_entries.append(db_entry)

        return db_entries

    async def retrieve(self, vector: list[float], k: int = 5) -> list[VectorDBEntry]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            k: The number of entries to retrieve.

        Returns:
            The retrieved entries.
        """
        collection = await self._get_chroma_collection()
        query_result = collection.query(query_embeddings=[vector], n_results=k, include=CHROMA_INCLUDE_KEYS)  # type: ignore
        return await self._extract_entries_from_query(query_result)

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

        collection = await self._get_chroma_collection()
        get_results = collection.get(where=where_chroma, limit=limit, offset=offset, include=CHROMA_INCLUDE_KEYS)  # type: ignore
        return await self._extract_entries_from_query(get_results)

    def __repr__(self) -> str:
        """
        Returns the string representation of the object.

        Returns:
            The string representation of the object.
        """
        return f"{self.__class__.__name__}(index_name={self._index_name})"
