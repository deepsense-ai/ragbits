from ragbits.core.embeddings.base import Embeddings
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.document_processor import DocumentProcessor
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser
from ragbits.document_search.retrieval.rerankers.base import Reranker
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker
from ragbits.document_search.vector_store.base import VectorStore


class DocumentSearch:
    """
    A main entrypoint to the DocumentSearch functionality.

    It provides methods for both ingestion and retrieval.

    Retrieval:

        1. Uses QueryRephraser to rephrase the query.
        2. Uses VectorStore to retrieve the most relevant chunks.
        3. Uses Reranker to rerank the chunks.
    """

    embedder: Embeddings

    vector_store: VectorStore

    query_rephraser: QueryRephraser
    reranker: Reranker

    def __init__(
        self,
        embedder: Embeddings,
        vector_store: VectorStore,
        query_rephraser: QueryRephraser | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.query_rephraser = query_rephraser or NoopQueryRephraser()
        self.reranker = reranker or NoopReranker()

    async def search(self, query: str) -> list[Element]:
        """
        Search for the most relevant chunks for a query.

        Args:
            query: The query to search for.

        Returns:
            A list of chunks.
        """
        queries = self.query_rephraser.rephrase(query)
        elements = []
        for rephrased_query in queries:
            search_vector = await self.embedder.embed_text([rephrased_query])
            # TODO: search parameters should be configurable
            entries = await self.vector_store.retrieve(search_vector[0], k=1)
            elements.extend([Element.from_vector_db_entry(entry) for entry in entries])

        return self.reranker.rerank(elements)

    async def ingest_document(self, document: DocumentMeta) -> None:
        """
        Ingest a document.

        Args:
            document: The document to ingest.
        """
        # TODO: This is a placeholder implementation. It should be replaced with a real implementation.

        document_processor = DocumentProcessor()
        elements = await document_processor.process(document)
        vectors = await self.embedder.embed_text([element.get_key() for element in elements])
        entries = [element.to_vector_db_entry(vector) for element, vector in zip(elements, vectors)]
        await self.vector_store.store(entries)
