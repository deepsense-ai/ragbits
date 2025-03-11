from collections.abc import Iterable

from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies.base import (
    ProcessingExecutionResult,
    ProcessingExecutionStrategy,
    ProcessingExecutionSummaryResult,
)
from ragbits.document_search.ingestion.providers.base import BaseProvider


class SequentialProcessing(ProcessingExecutionStrategy):
    """
    Processing execution strategy that processes documents in sequence, one at a time.
    """

    async def process(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> ProcessingExecutionResult:
        """
        Process documents for indexing sequentially one by one.

        Args:
            documents: The documents to process.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The processing excution result.
        """
        results = ProcessingExecutionResult()

        for document in documents:
            document_uri = document.metadata.id if isinstance(document, Document) else document.id
            try:
                elements = await self._parse_document(
                    document=document,
                    processor_router=processor_router,
                    processor_overwrite=processor_overwrite,
                )
                await self._remove_elements(
                    elements=elements,
                    vector_store=vector_store,
                )
                await self._insert_elements(
                    elements=elements,
                    vector_store=vector_store,
                )
            except Exception as exc:
                results.failed.append(
                    ProcessingExecutionSummaryResult(
                        document_uri=document_uri,
                        error=exc,
                    )
                )
            else:
                results.successful.append(
                    ProcessingExecutionSummaryResult(
                        document_uri=document_uri,
                        num_elements=len(elements),
                    )
                )

        return results
