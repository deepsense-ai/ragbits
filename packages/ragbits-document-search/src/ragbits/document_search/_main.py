import warnings
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from ragbits.core.embeddings import Embeddings, get_embeddings
from ragbits.core.vector_stores import VectorStore, get_vector_store
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element, ImageElement
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.retrieval.rephrasers import get_rephraser
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser
from ragbits.document_search.retrieval.rerankers import get_reranker
from ragbits.document_search.retrieval.rerankers.base import Reranker
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker


class SearchConfig(BaseModel):
    """
    Configuration for the search process.
    """

    reranker_kwargs: dict[str, Any] = Field(default_factory=dict)
    vector_store_kwargs: dict[str, Any] = Field(default_factory=dict)
    embedder_kwargs: dict[str, Any] = Field(default_factory=dict)


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
        document_processor_router: DocumentProcessorRouter | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.query_rephraser = query_rephraser or NoopQueryRephraser()
        self.reranker = reranker or NoopReranker()
        self.document_processor_router = document_processor_router or DocumentProcessorRouter.from_config()

    @classmethod
    def from_config(cls, config: dict) -> "DocumentSearch":
        """
        Creates and returns an instance of the DocumentSearch class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the DocumentSearch instance.

        Returns:
            DocumentSearch: An initialized instance of the DocumentSearch class.
        """
        embedder = get_embeddings(config["embedder"])
        query_rephraser = get_rephraser(config.get("rephraser"))
        reranker = get_reranker(config.get("reranker"))
        vector_store = get_vector_store(config["vector_store"])

        providers_config_dict: dict = config.get("providers", {})
        providers_config = DocumentProcessorRouter.from_dict_to_providers_config(providers_config_dict)
        document_processor_router = DocumentProcessorRouter.from_config(providers_config)

        return cls(embedder, vector_store, query_rephraser, reranker, document_processor_router)

    async def search(self, query: str, config: SearchConfig | None = None) -> list[Element]:
        """
        Search for the most relevant chunks for a query.

        Args:
            query: The query to search for.
            config: The search configuration.

        Returns:
            A list of chunks.
        """
        config = config or SearchConfig()
        queries = await self.query_rephraser.rephrase(query)
        elements = []
        for rephrased_query in queries:
            search_vector = await self.embedder.embed_text([rephrased_query])
            entries = await self.vector_store.retrieve(
                vector=search_vector[0],
                options=VectorStoreOptions(**config.vector_store_kwargs),
            )
            elements.extend([Element.from_vector_db_entry(entry) for entry in entries])

        return self.reranker.rerank(elements)

    async def _process_document(
        self,
        document: DocumentMeta | Document | Source,
        document_processor: BaseProvider | None = None,
    ) -> list[Element]:
        """
        Process a document and return the elements.

        Args:
            document: The document to process.
            document_processor: The document processor to use. If not provided, the document processor will be
                determined based on the document metadata.

        Returns:
            The elements.
        """
        if isinstance(document, Source):
            document_meta = await DocumentMeta.from_source(document)
        elif isinstance(document, DocumentMeta):
            document_meta = document
        else:
            document_meta = document.metadata

        if document_processor is None:
            document_processor = self.document_processor_router.get_provider(document_meta)

        document_processor = self.document_processor_router.get_provider(document_meta)
        return await document_processor.process(document_meta)

    async def ingest(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        document_processor: BaseProvider | None = None,
    ) -> None:
        """
        Ingest multiple documents.

        Args:
            documents: The documents or metadata of the documents to ingest.
            document_processor: The document processor to use. If not provided, the document processor will be
                determined based on the document metadata.
        """
        elements = []
        # TODO: Parallelize
        for document in documents:
            elements.extend(await self._process_document(document, document_processor))
        await self.insert_elements(elements)

    async def insert_elements(self, elements: list[Element]) -> None:
        """
        Insert Elements into the vector store.

        Args:
            elements: The list of Elements to insert.
        """
        vectors = await self.embedder.embed_text([element.get_key() for element in elements])

        image_elements = [element for element in elements if isinstance(element, ImageElement)]
        if image_elements and self.embedder.image_support():
            image_vectors = await self.embedder.embed_image([element.image_bytes for element in image_elements])
            vectors.extend(image_vectors)
        elif image_elements:
            warnings.warn(
                f"Image elements are not supported by the embedder {self.embedder}. "
                f"Skipping {len(image_elements)} image elements."
            )
        entries = [element.to_vector_db_entry(vector) for element, vector in zip(elements, vectors, strict=False)]

        await self.vector_store.store(entries)
