from collections.abc import Iterable

from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.strategies.base import (
    IngestExecutionResult,
    IngestStrategy,
    IngestSummaryResult,
)


class SequentialIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents in sequence, one at a time.
    """

    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> IngestExecutionResult:
        """
        Ingest documents sequentially one by one.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The ingest execution result.
        """
        results = IngestExecutionResult()

        for document in documents:
            document_uri = document.metadata.id if isinstance(document, Document) else document.id
            try:
                elements = await self._call_with_error_handling(
                    self._parse_document,
                    document=document,
                    processor_router=processor_router,
                    processor_overwrite=processor_overwrite,
                )
                await self._call_with_error_handling(
                    self._remove_elements,
                    elements=elements,  # type: ignore
                    vector_store=vector_store,
                )
                await self._call_with_error_handling(
                    self._insert_elements,
                    elements=elements,  # type: ignore
                    vector_store=vector_store,
                )
            except Exception as exc:
                results.failed.append(
                    IngestSummaryResult(
                        document_uri=document_uri,
                        error=exc,
                    )
                )
            else:
                results.successful.append(
                    IngestSummaryResult(
                        document_uri=document_uri,
                        num_elements=len(elements),  # type: ignore
                    )
                )

        return results
