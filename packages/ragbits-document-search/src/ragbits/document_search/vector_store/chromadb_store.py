import json
from copy import deepcopy
from hashlib import sha256
from typing import List, Literal, Optional, Union

try:
    import chromadb

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

from ragbits.core.embeddings.base import Embeddings
from ragbits.document_search.vector_store.base import VectorStore 
from ragbits.document_search.vector_store.in_memory import VectorDBEntry


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
        self._collection = self._get_chroma_collection()

        self._metadata = {"hnsw:space": distance_method}

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

    def _process_db_entry(self, entry: VectorDBEntry) -> tuple[str, list[float], str, dict]:
        doc_id = sha256(entry.key.encode("utf-8")).hexdigest()
        embedding = entry.vector
        text = entry.metadata["content"]

        metadata = deepcopy(entry.metadata)
        metadata["document"]["source"]["path"] = str(metadata["document"]["source"]["path"])
        metadata["key"] = entry.key
        metadata = {key: json.dumps(val) if isinstance(val, dict) else val for key, val in metadata.items()}

        return doc_id, embedding, text, metadata

    def _process_metadata(self, metadata: dict) -> dict[str, Union[str, int, float, bool]]:
        """
        Processes the metadata dictionary by parsing JSON strings if applicable.

        Args:
            metadata: A dictionary containing metadata where values may be JSON strings.

        Returns:
            A dictionary with the same keys as the input, where JSON strings are parsed into their respective Python data types.
        """
        return {key: json.loads(val) if self._is_json(val) else val for key, val in metadata.items()}

    def _is_json(self, myjson: str) -> bool:
        """
        Check if the provided string is a valid JSON.

        Args:
            myjson: The string to be checked.

        Returns:
            True if the string is a valid JSON, False otherwise.
        """
        try:
            if isinstance(myjson, str):
                json.loads(myjson)
                return True
            return False
        except ValueError:
            return False

    async def store(self, entries: List[VectorDBEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        collection = self._get_chroma_collection()

        entries_processed = list(map(self._process_db_entry, entries))
        ids, embeddings, texts, metadatas = map(list, zip(*entries_processed))

        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    async def retrieve(self, vector: List[float], k: int = 5) -> List[VectorDBEntry]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            k: The number of entries to retrieve.

        Returns:
            The retrieved entries.
        """
        collection = self._get_chroma_collection()
        query_result = collection.query(query_embeddings=[vector], n_results=k)

        db_entries = []
        for meta in query_result.get("metadatas"):
            db_entry = VectorDBEntry(
                key=meta[0].get("key"),
                vector=vector,
                metadata=self._process_metadata(meta[0]),
            )

            db_entries.append(db_entry)

        return db_entries

    async def find_similar(self, text: str) -> Optional[str]:
        """
        Finds the most similar text in the chroma collection or returns None if the most similar text
        has distance bigger than `self.max_distance`.

        Args:
            text: The text to find similar to.

        Returns:
            The most similar text or None if no similar text is found.
        """

        collection = self._get_chroma_collection()

        if isinstance(self._embedding_function, Embeddings):
            embedding = await self._embedding_function.embed_text([text])
            retrieved = collection.query(query_embeddings=embedding, n_results=1)
        else:
            retrieved = collection.query(query_texts=[text], n_results=1)

        return self._return_best_match(retrieved)

    def __repr__(self) -> str:
        """
        Returns the string representation of the object.

        Returns:
            The string representation of the object.
        """
        return f"{self.__class__.__name__}(index_name={self._index_name})"
