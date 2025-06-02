import asyncio
from collections.abc import Iterable
from dataclasses import dataclass

from ragbits.core.sources.base import Source
from ragbits.core.utils.helpers import batched
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.strategies.base import (
    IngestDocumentResult,
    IngestError,
    IngestExecutionResult,
    IngestStrategy,
)


@dataclass
class IngestTaskResult:
    """
    Represents the result of the document batch ingest task.
    """

    document_uri: str
    elements: list[Element]


class BatchedIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents in batches.
    """

    def __init__(
        self,
        batch_size: int | None = None,
        enrich_batch_size: int | None = None,
        index_batch_size: int | None = None,
        num_retries: int = 3,
        backoff_multiplier: int = 1,
        backoff_max: int = 60,
    ) -> None:
        """
        Initialize the BatchedIngestStrategy instance.

        Args:
            batch_size: The batch size for parsing documents.
                Describes the maximum number of documents to parse at once. If None, all documents are parsed at once.
            enrich_batch_size: The batch size for enriching elements.
                Describes the maximum number of document elements to enrich at once.
                If None, all elements are enriched at once.
            index_batch_size: The batch size for indexing elements.
                Describes the maximum number of document elements to index at once.
                If None, all elements are indexed at once.
            num_retries: The number of retries per document ingest task error.
            backoff_multiplier: The base delay multiplier for exponential backoff (in seconds).
            backoff_max: The maximum allowed delay (in seconds) between retries.
        """
        super().__init__(num_retries=num_retries, backoff_multiplier=backoff_multiplier, backoff_max=backoff_max)
        self.batch_size = batch_size
        self.enrich_batch_size = enrich_batch_size
        self.index_batch_size = index_batch_size

    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        parser_router: DocumentParserRouter,
        enricher_router: ElementEnricherRouter,
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

        for documents_batch in batched(documents, self.batch_size):
            # Parse documents
            parse_results = await self._parse_batch(documents_batch, parser_router)

            # Split documents into successful and failed
            successfully_parsed = [result for result in parse_results if isinstance(result, IngestTaskResult)]
            failed_parsed = [result for result in parse_results if isinstance(result, IngestDocumentResult)]

            # Further split successful documents into to enrich and ready
            to_enrich = [
                result
                for result in successfully_parsed
                if any(type(element) in enricher_router for element in result.elements)
            ]
            ready_parsed = [
                result
                for result in successfully_parsed
                if not any(type(element) in enricher_router for element in result.elements)
            ]

            # Enrich documents
            enrich_results = await self._enrich_batch(to_enrich, enricher_router)

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
        parser_router: DocumentParserRouter,
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

        results: list[IngestTaskResult | IngestDocumentResult] = []
        for uri, response in zip(uris, responses, strict=True):
            if isinstance(response, BaseException):
                if isinstance(response, Exception):
                    results.append(
                        IngestDocumentResult(
                            document_uri=uri,
                            error=IngestError.from_exception(response),
                        )
                    )
                # Handle only standard exceptions, not BaseExceptions like SystemExit, KeyboardInterrupt, etc.
                else:
                    raise response
            else:
                results.append(
                    IngestTaskResult(
                        document_uri=uri,
                        elements=response,
                    )
                )

        return results

    async def _enrich_batch(
        self,
        batch: list[IngestTaskResult],
        enricher_router: ElementEnricherRouter,
    ) -> list[IngestTaskResult | IngestDocumentResult]:
        """
        Enrich batch of documents.

        Args:
            batch: The documents to enrich.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The task results.
        """

        async def _enrich_document(result: IngestTaskResult) -> IngestTaskResult | IngestDocumentResult:
            try:
                enriched_elements = [
                    element
                    for elements_batch in batched(result.elements, self.enrich_batch_size)
                    for element in await self._call_with_error_handling(
                        self._enrich_elements,
                        elements=elements_batch,
                        enricher_router=enricher_router,
                    )
                ]
                return IngestTaskResult(
                    document_uri=result.document_uri,
                    elements=enriched_elements,
                )
            except Exception as exc:
                return IngestDocumentResult(
                    document_uri=result.document_uri,
                    error=IngestError.from_exception(exc),
                )

        return await asyncio.gather(*[_enrich_document(result) for result in batch])

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

        async def _index_document(result: IngestTaskResult) -> IngestDocumentResult:
            try:
                await self._call_with_error_handling(
                    self._remove_elements,
                    document_ids=[result.document_uri],
                    vector_store=vector_store,
                )
                for elements_batch in batched(result.elements, self.index_batch_size):
                    await self._call_with_error_handling(
                        self._insert_elements,
                        elements=elements_batch,
                        vector_store=vector_store,
                    )
                return IngestDocumentResult(
                    document_uri=result.document_uri,
                    num_elements=len(result.elements),
                )
            except Exception as exc:
                return IngestDocumentResult(
                    document_uri=result.document_uri,
                    error=IngestError.from_exception(exc),
                )

        return await asyncio.gather(*[_index_document(result) for result in batch])
