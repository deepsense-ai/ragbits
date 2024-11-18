import asyncio
from collections.abc import Sequence

from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider

from .base import ProcessingExecutionStrategy


class BatchedAsyncProcessing(ProcessingExecutionStrategy):
    """
    A processing execution strategy that processes documents asynchronously in batches.
    """

    def __init__(self, batch_size: int = 10):
        """
        Initialize the BatchedAsyncProcessing instance.

        Args:
            batch_size: The size of the batch to process documents in.
        """
        self.batch_size = batch_size

    async def _process_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        document: DocumentMeta | Document | Source,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        async with semaphore:
            return await self.process_document(document, processor_router, processor_overwrite)

    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        """
        Process documents using the given processor and return the resulting elements.

        Args:
            documents: The documents to process.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.

        Returns:
            A list of elements.
        """
        semaphore = asyncio.Semaphore(self.batch_size)

        responses = await asyncio.gather(
            *[
                self._process_with_semaphore(semaphore, document, processor_router, processor_overwrite)
                for document in documents
            ]
        )

        # Return a flattened list of elements
        return [element for response in responses for element in response]
