import asyncio
from collections.abc import Sequence

import ray

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
        """Process multiple documents asynchronously using Ray distributed computing framework.

        This method processes a sequence of documents in parallel using Ray distributed computing capabilities.
        Each document is processed remotely as a separate Ray task.

        Args:
            documents (Sequence[DocumentMeta | Document | Source]): A sequence of documents to process,
                can be DocumentMeta, Document or Source objects
            processor_router (DocumentProcessorRouter): Router that determines which processor to use for each document
            processor_overwrite (BaseProvider | None, optional): Provider to override the default processor.

        Returns:
            list[Element]: List of processed elements, one for each input document

        Raises:
            RayNotInitializedException: If Ray framework is not initialized
        """
        process_document_remotely = ray.remote(self.process_document)

        tasks = [
            process_document_remotely.remote(document, processor_router, processor_overwrite)  # type: ignore[call-arg]
            for document in documents
        ]
        results = await asyncio.gather(*tasks)
        return results  # type: ignore[return-value]
