import asyncio
from collections.abc import Iterable
from itertools import islice

from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider

from .base import IngestStrategy, ProcessingExecutionResult, ProcessingExecutionSummaryResult


class BatchedIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents in batches.
    """

    def __init__(self, batch_size: int = 10, num_retries: int = 3) -> None:
        """
        Initialize the BatchedIngestStrategy instance.

        Args:
            batch_size: The size of the batch to process documents in.
            num_retries: The number of retries per document processing task error.
        """
        super().__init__(num_retries=num_retries)
        self.batch_size = batch_size

    async def process(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> ProcessingExecutionResult:
        """
        Process documents for indexing sequentially in batches.

        Args:
            documents: The documents to process.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The processing excution result.
        """
        results = ProcessingExecutionResult()
        iterator = iter(documents)

        while batch := list(islice(iterator, self.batch_size)):
            document_uris = [
                document.metadata.id if isinstance(document, Document) else document.id for document in batch
            ]
            responses = await asyncio.gather(
                *[
                    self._parse_document(
                        document=document,
                        processor_router=processor_router,
                        processor_overwrite=processor_overwrite,
                    )
                    for document in batch
                ],
                return_exceptions=True,
            )
            results.failed.extend(
                ProcessingExecutionSummaryResult(
                    document_uri=uri,
                    error=response,
                )
                for uri, response in zip(document_uris, responses, strict=False)
                if isinstance(response, BaseException)
            )
            elements = [
                element for response in responses if not isinstance(response, BaseException) for element in response
            ]

            try:
                await self._remove_elements(
                    elements=elements,
                    vector_store=vector_store,
                )
                await self._insert_elements(
                    elements=elements,
                    vector_store=vector_store,
                )
            except Exception as exc:
                results.failed.extend(
                    ProcessingExecutionSummaryResult(
                        document_uri=uri,
                        error=exc,
                    )
                    for uri, response in zip(document_uris, responses, strict=False)
                    if not isinstance(response, BaseException)
                )
            else:
                results.successful.extend(
                    ProcessingExecutionSummaryResult(
                        document_uri=uri,
                        num_elements=len(response),
                    )
                    for uri, response in zip(document_uris, responses, strict=False)
                    if not isinstance(response, BaseException)
                )

        return results
