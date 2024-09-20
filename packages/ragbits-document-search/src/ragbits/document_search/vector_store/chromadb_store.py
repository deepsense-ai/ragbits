from hashlib import sha256
from typing import Literal, Optional, Union

import chromadb

from document_search.ingestion.embeddings.base import Embedder
from document_search.utils.custom_types import Chunk, EmbeddedChunk, InMemoryDocument, Location
from document_search.utils.vector_stores.base import VectorStore


class ChromaDBStore(VectorStore):
    """Class that stores text embeddings using [Chroma](https://docs.trychroma.com/)"""

    def __init__(
        self,
        index_name: str,
        chroma_client: chromadb.ClientAPI,
        embedding_function: Union[Embedder, chromadb.EmbeddingFunction],
        max_distance: Optional[float] = None,
        distance_method: Literal["l2", "ip", "cosine"] = "l2",
    ):
        """
        Initializes the ChromaDBStore with the given parameters.

        Args:
            index_name (str): The name of the index.
            chroma_client (chromadb.ClientAPI): The ChromaDB client.
            embedding_function (Union[Embedder, chromadb.EmbeddingFunction]): The embedding function.
            max_distance (Optional[float], default=None): The maximum distance for similarity.
            distance_method (Literal["l2", "ip", "cosine"], default="l2"): The distance method to use.
        """
        super().__init__()
        self.index_name = index_name
        self.chroma_client = chroma_client
        self.embedding_function = embedding_function
        self.max_distance = max_distance

        self._metadata = {"hnsw:space": distance_method}

    def _get_chroma_collection(self) -> chromadb.Collection:
        """
        Based on the selected embedding_function, chooses how to retrieve the ChromaDB collection.
        If the collection doesn't exist, it creates one.

        Returns:
            chromadb.Collection: Retrieved collection
        """
        if isinstance(self.embedding_function, Embedder):
            return self.chroma_client.get_or_create_collection(name=self.index_name, metadata=self._metadata)

        return self.chroma_client.get_or_create_collection(
            name=self.index_name,
            metadata=self._metadata,
            embedding_function=self.embedding_function,
        )

    def _return_best_match(self, retrieved: dict) -> Optional[str]:
        """
        Based on the retrieved data, returns the best match or None if no match is found.

        Args:
            retrieved (dict): Retrieved data, with a column-first format

        Returns:
            Optional[str]: The best match or None if no match is found
        """
        if self.max_distance is None or retrieved["distances"][0][0] <= self.max_distance:
            return retrieved["documents"][0][0]

        return None

    async def store_embedded_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        """
        Stores embedded chunks in the ChromaDB collection.

        Args:
            embedded_chunks (list[EmbeddedChunk]): The embedded chunks to store.
        """
        formatted_data = [
            {
                "text": emb_chunk.chunk.content,
                "metadata": {
                    "location": emb_chunk.chunk.location.model_dump_json(),
                    "title": emb_chunk.document.title,
                },
            }
            for emb_chunk in embedded_chunks
        ]
        await self._store(formatted_data)

    async def _store(self, data: list[dict]) -> None:
        """
        Fills chroma collection with embeddings of provided string. As the id uses hash value of the string.

        Args:
            data (list[dict]): The data to store.
        """
        ids = [sha256(item["text"].encode("utf-8")).hexdigest() for item in data]
        texts = [item["text"] for item in data]
        metadata = [item["metadata"] for item in data]

        collection = self._get_chroma_collection()

        if isinstance(self.embedding_function, Embedder):
            embeddings = await self.embedding_function.embed_text(texts)
            collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadata)
        else:
            collection.add(ids=ids, documents=texts, metadatas=metadata)

    async def find_similar(self, text: str) -> Optional[str]:
        """
        Finds the most similar text in the chroma collection or returns None if the most similar text
        has distance bigger than `self.max_distance`.

        Args:
            text (str): The text to find similar to.

        Returns:
            Optional[str]: The most similar text or None if no similar text is found.
        """

        collection = self._get_chroma_collection()

        if isinstance(self.embedding_function, Embedder):
            embedding = await self.embedding_function.embed_text([text])
            retrieved = collection.query(query_embeddings=embedding, n_results=1)
        else:
            retrieved = collection.query(query_texts=[text], n_results=1)

        return self._return_best_match(retrieved)

    def retrieve(self, vector: list[float]) -> list[Chunk]:
        """
        Retrieves documents based on vector embeddings.

        Args:
            vector (list[float]): The vector to query.

        Returns:
            list[Chunk]: A list of `Chunk` objects.
        """
        collection = self._get_chroma_collection()
        chunks = []
        query_result = collection.query(query_embeddings=vector, n_results=1)

        for doc, meta in zip(query_result.get("documents"), query_result.get("metadatas")):
            chunk = Chunk(
                content=doc[0],
                document=InMemoryDocument(title=meta[0].get("title"), content=doc[0]),
                location=Location.model_validate_json(meta[0].get("location")),
            )
            chunks.append(chunk)
        return chunks

    def __repr__(self) -> str:
        """
        Returns the string representation of the object.

        Returns:
            str: The string representation of the object.
        """
        return f"{self.__class__.__name__}(index_name={self.index_name})"
