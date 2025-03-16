from collections.abc import Iterable

from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import IntermediateElement
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.intermediate_handlers.base import BaseIntermediateHandler
from ragbits.document_search.ingestion.strategies.base import (
    IngestDocumentResult,
    IngestExecutionResult,
    IngestStrategy,
)


class SequentialIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents in sequence, one at a time.
    """

    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        parser_router: DocumentProcessorRouter,
        enricher_router: dict[type[IntermediateElement], BaseIntermediateHandler],
    ) -> IngestExecutionResult:
        """
        Ingest documents sequentially one by one.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            parser_router: The document parser router to use.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The ingest execution result.
        """
        results = IngestExecutionResult()

        for document in documents:
            document_uri = document.metadata.id if isinstance(document, Document) else document.id
            try:
                parsed_elements = await self._call_with_error_handling(
                    self._parse_document,
                    document=document,
                    parser_router=parser_router,
                )
                enriched_elements = await self._call_with_error_handling(
                    self._enrich_elements,
                    elements=[element for element in parsed_elements if isinstance(element, IntermediateElement)],
                    enricher_router=enricher_router,
                )
                elements = [
                    element for element in parsed_elements if not isinstance(element, IntermediateElement)
                ] + enriched_elements

                await self._call_with_error_handling(
                    self._remove_elements,
                    elements=elements,
                    vector_store=vector_store,
                )
                await self._call_with_error_handling(
                    self._insert_elements,
                    elements=elements,
                    vector_store=vector_store,
                )
            except Exception as exc:
                results.failed.append(
                    IngestDocumentResult(
                        document_uri=document_uri,
                        error=exc,
                    )
                )
            else:
                results.successful.append(
                    IngestDocumentResult(
                        document_uri=document_uri,
                        num_elements=len(elements),
                    )
                )

        return results
