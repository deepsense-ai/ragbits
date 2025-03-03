from collections.abc import Sequence

from ragbits.core.embeddings.base import Embeddings
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider

from .base import ProcessingExecutionStrategy


class SequentialProcessing(ProcessingExecutionStrategy):
    """
    A processing execution strategy that processes documents in sequence, one at a time.
    """

    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        embedder: Embeddings,
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> None:
        """
        Process documents using the given processor and return the resulting elements.

        Args:
            documents: The documents to process.
            embedder: The embedder to produce chunk embeddings.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.

        Returns:
            A list of elements.
        """
        for document in documents:
            await self.process_document(
                document=document,
                embedder=embedder,
                vector_store=vector_store,
                processor_router=processor_router,
                processor_overwrite=processor_overwrite,
            )
