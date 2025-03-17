import asyncio
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import islice

from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element, IntermediateElement
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.intermediate_handlers.base import BaseIntermediateHandler
from ragbits.document_search.ingestion.strategies.base import (
    IngestDocumentResult,
    IngestExecutionResult,
    IngestStrategy,
)


@dataclass
class IngestTaskResult:
    """
    Represents the result of the document batch ingest tast.
    """

    document_uri: str
    elements: Sequence[Element | IntermediateElement]


class BatchedIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents in batches.
    """

    def __init__(
        self,
        batch_size: int = 10,
        num_retries: int = 3,
        backoff_multiplier: int = 1,
        backoff_max: int = 60,
    ) -> None:
        """
        Initialize the BatchedIngestStrategy instance.

        Args:
            batch_size: The size of the batch to ingest documents in.
            num_retries: The number of retries per document ingest task error.
            backoff_multiplier: The base delay multiplier for exponential backoff (in seconds).
            backoff_max: The maximum allowed delay (in seconds) between retries.
        """
        super().__init__(num_retries=num_retries, backoff_multiplier=backoff_multiplier, backoff_max=backoff_max)
        self.batch_size = batch_size

    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        parser_router: DocumentProcessorRouter,
        enricher_router: dict[type[IntermediateElement], BaseIntermediateHandler],
    ) -> IngestExecutionResult:
        """
        Ingest documents sequentially in batches.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            parser_router: The document parser router to use.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The ingest execution result.
        """
        results = IngestExecutionResult()
        documents_iterator = iter(documents)

        while batch := list(islice(documents_iterator, self.batch_size)):
            # Parse documents
            parse_results = await self._parse_batch(batch, parser_router)

            # Split documents into successful and failed
            successfully_parsed = [result for result in parse_results if isinstance(result, IngestTaskResult)]
            failed_parsed = [result for result in parse_results if isinstance(result, IngestDocumentResult)]

            # Further split successful documents into intermediate and ready
            intermediate_parsed = [
                result
                for result in successfully_parsed
                if any(isinstance(element, IntermediateElement) for element in result.elements)
            ]
            ready_parsed = [
                result
                for result in successfully_parsed
                if not any(isinstance(element, IntermediateElement) for element in result.elements)
            ]

            # Enrich intermediate documents
            enrich_results = await self._enrich_batch(intermediate_parsed, enricher_router)

            # Split enriched documents into successful and failed
            successfully_enriched = [result for result in enrich_results if isinstance(result, IngestTaskResult)]
            failed_enriched = [result for result in enrich_results if isinstance(result, IngestDocumentResult)]

            # Combine ready documents with successfully enriched documents for indexing
            to_index = ready_parsed + successfully_enriched

            # Index the combined documents
            index_results = await self._index_batch(to_index, vector_store)

            # Split indexed documents into successful and failed
            successfully_indexed = [result for result in index_results if not result.error]
            failed_indexed = [result for result in index_results if result.error]

            # Combine all failed documents
            all_failed = failed_parsed + failed_enriched + failed_indexed

            # Update the final result
            results.successful.extend(successfully_indexed)
            results.failed.extend(all_failed)

        return results

    async def _parse_batch(
        self,
        batch: list[DocumentMeta | Document | Source],
        parser_router: DocumentProcessorRouter,
    ) -> list[IngestTaskResult | IngestDocumentResult]:
        """
        Parse batch of documents.

        Args:
            batch: The documents to parse.
            parser_router: The document parser router to use.

        Returns:
            The task results.
        """
        uris = [document.metadata.id if isinstance(document, Document) else document.id for document in batch]
        responses = await asyncio.gather(
            *[
                self._call_with_error_handling(
                    self._parse_document,
                    document=document,
                    parser_router=parser_router,
                )
                for document in batch
            ],
            return_exceptions=True,
        )
        return [
            IngestDocumentResult(
                document_uri=uri,
                error=response,
            )
            if isinstance(response, BaseException)
            else IngestTaskResult(
                document_uri=uri,
                elements=response,
            )
            for uri, response in zip(uris, responses, strict=True)
        ]

    async def _enrich_batch(
        self,
        batch: list[IngestTaskResult],
        enricher_router: dict[type[IntermediateElement], BaseIntermediateHandler],
    ) -> list[IngestTaskResult | IngestDocumentResult]:
        """
        Enrich batch of documents.

        Args:
            batch: The documents to enrich.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The task results.
        """
        responses = await asyncio.gather(
            *[
                self._call_with_error_handling(
                    self._enrich_elements,
                    elements=[element for element in result.elements if isinstance(element, IntermediateElement)],
                    enricher_router=enricher_router,
                )
                for result in batch
            ],
            return_exceptions=True,
        )
        return [
            IngestDocumentResult(
                document_uri=result.document_uri,
                error=response,
            )
            if isinstance(response, BaseException)
            else IngestTaskResult(
                document_uri=result.document_uri,
                elements=[element for element in result.elements if isinstance(element, Element)] + response,
            )
            for result, response in zip(batch, responses, strict=True)
        ]

    async def _index_batch(
        self,
        batch: list[IngestTaskResult],
        vector_store: VectorStore,
    ) -> list[IngestDocumentResult]:
        """
        Index batch of documents.

        Args:
            batch: The documents to index.
            vector_store: The vector store to store document chunks.

        Returns:
            The task results.
        """
        elements = [
            element for result in batch for element in result.elements if not isinstance(element, IntermediateElement)
        ]
        try:
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
            return [
                IngestDocumentResult(
                    document_uri=result.document_uri,
                    error=exc,
                )
                for result in batch
            ]
        return [
            IngestDocumentResult(
                document_uri=result.document_uri,
                num_elements=len(result.elements),
            )
            for result in batch
        ]
