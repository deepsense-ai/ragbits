import json
from hashlib import sha256
from typing import List, Literal, Optional, Union

try:
    import chromadb

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

from ragbits.core.embeddings.base import Embeddings
from ragbits.core.utils import get_cls_from_config
from ragbits.core.vector_store.base import VectorStore
from ragbits.core.vector_store.in_memory import VectorDBEntry


class ChromaDBStore(VectorStore):
    """Class that stores text embeddings using [Chroma](https://docs.trychroma.com/)"""

    def __init__(
        self,
        index_name: str,
        chroma_client: chromadb.ClientAPI,
        embedding_function: Union[Embeddings, chromadb.EmbeddingFunction],
        max_distance: Optional[float] = None,
        distance_method: Literal["l2", "ip", "cosine"] = "l2",
    ):
        """
        Initializes the ChromaDBStore with the given parameters.

        Args:
            index_name: The name of the index.
            chroma_client: The ChromaDB client.
            embedding_function: The embedding function.
            max_distance: The maximum distance for similarity.
            distance_method: The distance method to use.
        """
        if not HAS_CHROMADB:
            raise ImportError("Install the 'ragbits-document-search[chromadb]' extra to use LiteLLM embeddings models")

        super().__init__()
        self._index_name = index_name
        self._chroma_client = chroma_client
        self._embedding_function = embedding_function
        self._max_distance = max_distance
        self._metadata = {"hnsw:space": distance_method}
        self._collection = self._get_chroma_collection()

    @classmethod
    def from_config(cls, config: dict) -> "ChromaDBStore":
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
            distance_method=config.get("distance_method", "l2"),
        )

    def _get_chroma_collection(self) -> chromadb.Collection:
        """
        Based on the selected embedding_function, chooses how to retrieve the ChromaDB collection.
        If the collection doesn't exist, it creates one.

        Returns:
            Retrieved collection
        """
        if isinstance(self._embedding_function, Embeddings):
            return self._chroma_client.get_or_create_collection(name=self._index_name, metadata=self._metadata)

        return self._chroma_client.get_or_create_collection(
            name=self._index_name,
            metadata=self._metadata,
            embedding_function=self._embedding_function,
        )

    def _return_best_match(self, retrieved: dict) -> Optional[str]:
        """
        Based on the retrieved data, returns the best match or None if no match is found.

        Args:
            Retrieved data, with a column-first format

        Returns:
            The best match or None if no match is found
        """
        if self._max_distance is None or retrieved["distances"][0][0] <= self._max_distance:
            return retrieved["documents"][0][0]

        return None

    def _process_db_entry(self, entry: VectorDBEntry) -> tuple[str, list[float], dict]:
        doc_id = sha256(entry.key.encode("utf-8")).hexdigest()
        embedding = entry.vector

        metadata = {
            "__key": entry.key,
            "__metadata": json.dumps(entry.metadata, default=str),
        }

        return doc_id, embedding, metadata

    @property
    def embedding_function(self) -> Union[Embeddings, chromadb.EmbeddingFunction]:
        """
        Returns the embedding function.

        Returns:
            The embedding function.
        """
        return self._embedding_function

    async def store(self, entries: List[VectorDBEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        entries_processed = list(map(self._process_db_entry, entries))
        ids, embeddings, metadatas = map(list, zip(*entries_processed))

        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)

    async def retrieve(self, vector: List[float], k: int = 5) -> List[VectorDBEntry]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            k: The number of entries to retrieve.

        Returns:
            The retrieved entries.
        """
        query_result = self._collection.query(query_embeddings=[vector], n_results=k)

        db_entries = []
        for meta in query_result.get("metadatas"):
            db_entry = VectorDBEntry(
                key=meta[0]["__key"],
                vector=vector,
                metadata=json.loads(meta[0]["__metadata"]),
            )

            db_entries.append(db_entry)

        return db_entries

    def __repr__(self) -> str:
        """
        Returns the string representation of the object.

        Returns:
            The string representation of the object.
        """
        return f"{self.__class__.__name__}(index_name={self._index_name})"
