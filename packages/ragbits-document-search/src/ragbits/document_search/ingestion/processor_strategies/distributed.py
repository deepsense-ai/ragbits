from collections.abc import Iterable

# try:
#     import ray
#     HAS_RAY = True
# except ImportError:
#     HAS_RAY = False
from ragbits.core.embeddings.base import Embedder
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies.base import (
    ProcessingExecutionResult,
    ProcessingExecutionStrategy,
)
from ragbits.document_search.ingestion.providers.base import BaseProvider


class DistributedProcessing(ProcessingExecutionStrategy):
    """
    Processing execution strategy that processes documents on a cluster, using Ray.
    """

    def __init__(self, batch_size: int = 10, num_retries: int = 3) -> None:
        """
        Initialize the DistributedProcessing instance.

        Args:
            batch_size: The size of the batch to process documents in.
            num_retries: The number of retries per document processing task error.
        """
        super().__init__(num_retries=num_retries)
        self.batch_size = batch_size

    async def process(  # noqa: PLR6301
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> ProcessingExecutionResult:
        """
        Process documents for indexing in parallel in batches.

        Args:
            documents: The documents to process.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The processing excution result.
        """
        # @ray.remote
        # def process_documents_remotely(documents: Iterable[DocumentMeta | Document | Source]) -> list[Element]:
        #     async def process_batch() -> list[list[Element]]:
        #         tasks = [
        #             self._parse_document(document, processor_router, processor_overwrite) for document in documents
        #         ]
        #         return await asyncio.gather(*tasks)

        #     results = asyncio.run(process_batch())
        #     return sum(results, [])

        # tasks = []
        # iterator = iter(documents)

        # while batch := list(islice(iterator, self.batch_size)):
        #     tasks.append(process_documents_remotely.remote(batch))

        # elements = sum(await asyncio.gather(*tasks), [])
        return ProcessingExecutionResult()
