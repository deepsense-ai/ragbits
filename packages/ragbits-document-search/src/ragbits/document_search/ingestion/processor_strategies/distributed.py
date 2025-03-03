import asyncio
from collections.abc import Sequence

from ragbits.core.vector_stores.base import VectorStore

try:
    import ray

    HAS_RAY = True
except ImportError:
    HAS_RAY = False

from ragbits.core.embeddings.base import Embeddings
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies.base import ProcessingExecutionStrategy
from ragbits.document_search.ingestion.providers.base import BaseProvider


class DistributedProcessing(ProcessingExecutionStrategy):
    """
    A processing execution strategy that processes documents on a cluster, using Ray.
    """

    def __init__(self, batch_size: int = 10):
        """
        Initialize the DistributedProcessing instance.

        Args:
            batch_size: The size of the batch to process documents in.
            It defaults to 10, but should be increased if the document processing is trivial (< 1s per batch).

        Raises:
            ModuleNotFoundError: If Ray is not installed.
        """
        if not HAS_RAY:
            raise ModuleNotFoundError(
                "You need to install the 'distributed' extra requirements to use Ray distributed computing"
            )

        self.batch_size = batch_size

    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        embedder: Embeddings,
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> None:
        """Process multiple documents in parallel using Ray distributed computing framework.

        This method processes a sequence of documents in parallel using Ray distributed computing capabilities.
        Each document is processed remotely as a separate Ray task.

        Args:
            documents: The documents to process.
            embedder: The embedder to produce chunk embeddings.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.
        """

        @ray.remote
        def process_document_remotely(documents: Sequence[DocumentMeta | Document | Source]) -> None:
            async def process_batch() -> None:
                tasks = [
                    self.process_document(
                        document=document,
                        embedder=embedder,
                        vector_store=vector_store,
                        processor_router=processor_router,
                        processor_overwrite=processor_overwrite,
                    )
                    for document in documents
                ]
                await asyncio.gather(*tasks)

            asyncio.run(process_batch())

        tasks = []
        for i in range(0, len(documents), self.batch_size):
            tasks.append(process_document_remotely.remote(documents[i : i + self.batch_size]))

        await asyncio.gather(*tasks)
