import asyncio
from collections.abc import Sequence

from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies.base import ProcessingExecutionStrategy
from ragbits.document_search.ingestion.providers.base import BaseProvider


class DistributedProcessing(ProcessingExecutionStrategy):
    """
    A processing execution strategy that processes documents on a cluster, using Ray.
    """

    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        """Process multiple documents in parallel using Ray distributed computing framework.

        This method processes a sequence of documents in parallel using Ray distributed computing capabilities.
        Each document is processed remotely as a separate Ray task.

        Args:
            documents: The documents to process.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.

        Raises:
            ModuleNotFoundError: If Ray is not installed
        """
        import ray

        @ray.remote
        def process_document_remotely(document: DocumentMeta | Document | Source) -> list[Element]:
            return asyncio.run(self.process_document(document, processor_router, processor_overwrite))

        tasks = [process_document_remotely.remote(document) for document in documents]

        return sum(await asyncio.gather(*tasks), [])
