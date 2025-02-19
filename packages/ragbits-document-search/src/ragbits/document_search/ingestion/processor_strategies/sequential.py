from collections.abc import Sequence

from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
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
        elements = []
        for document in documents:
            elements.extend(await self.process_document(document, processor_router, processor_overwrite))
        return elements
