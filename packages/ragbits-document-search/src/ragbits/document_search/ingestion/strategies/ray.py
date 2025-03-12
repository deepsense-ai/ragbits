import asyncio
from collections.abc import Iterable

from ragbits.core.utils.decorators import requires_dependencies
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.strategies.base import (
    IngestExecutionResult,
    IngestStrategy,
    IngestSummaryResult,
    IngestTaskResult,
)


class RayDistributedIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents on a cluster, using Ray.
    """

    def __init__(
        self,
        cpu_batch_size: int = 1,
        cpu_memory: float | None = None,
        io_batch_size: int = 10,
        io_memory: float | None = None,
        num_retries: int = 3,
    ) -> None:
        """
        Initialize the RayDistributedIngestStrategy instance.

        Args:
            cpu_batch_size: The batch size for CPU bound tasks (e.g. parsing).
            cpu_memory: The heap memory in bytes to reserve for each parallel CPU bound tasks (e.g. parsing).
            io_batch_size: The batch size for IO bound tasks (e.g. indexing).
            io_memory: The heap memory in bytes to reserve for each parallel IO bound tasks (e.g. indexing).
            num_retries: The number of retries per document ingest task error.
        """
        super().__init__(num_retries=num_retries)
        self.cpu_batch_size = cpu_batch_size
        self.cpu_memory = cpu_memory
        self.io_batch_size = io_batch_size
        self.io_memory = io_memory

    @requires_dependencies(["ray.data"], "ray")
    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> IngestExecutionResult:
        """
        Ingest documents in parallel in batches.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The ingest execution result.
        """
        import ray

        def _parse(batch: dict[str, list[DocumentMeta | Document | Source]]) -> dict:
            async def _main() -> dict:
                document_uris = [
                    document.metadata.id if isinstance(document, Document) else document.id
                    for document in batch["item"]
                ]
                responses = await asyncio.gather(
                    *[
                        self._parse_document(
                            document=document,
                            processor_router=processor_router,
                            processor_overwrite=processor_overwrite,
                        )
                        for document in batch["item"]
                    ],
                    return_exceptions=True,
                )
                return {
                    "results": [
                        IngestTaskResult(
                            document_uri=uri,
                            response=response,
                        )
                        for uri, response in zip(document_uris, responses, strict=False)
                    ]
                }

            return asyncio.run(_main())

        def _remove(batch: dict) -> dict:
            async def _main() -> dict:
                elements = [
                    element
                    for result in batch["results"]
                    if not isinstance(result.response, BaseException)
                    for element in result.response
                ]
                try:
                    await self._remove_elements(
                        elements=elements,
                        vector_store=vector_store,
                    )
                except Exception as exc:
                    batch["results"] = [
                        IngestTaskResult(
                            document_uri=result.document_uri,
                            response=exc,
                        )
                        if not isinstance(result.response, BaseException)
                        else result
                        for result in batch["results"]
                    ]
                return batch

            return asyncio.run(_main())

        def _insert(batch: dict) -> dict:
            async def _main() -> dict:
                elements = [
                    element
                    for result in batch["results"]
                    if not isinstance(result.response, BaseException)
                    for element in result.response
                ]
                try:
                    await self._insert_elements(
                        elements=elements,
                        vector_store=vector_store,
                    )
                except Exception as exc:
                    batch["results"] = [
                        IngestTaskResult(
                            document_uri=result.document_uri,
                            response=exc,
                        )
                        if not isinstance(result.response, BaseException)
                        else result
                        for result in batch["results"]
                    ]
                return batch

            return asyncio.run(_main())

        def _summarize(batch: dict) -> dict:
            return {
                "results": [
                    IngestSummaryResult(
                        document_uri=result.document_uri,
                        error=result.response,
                    )
                    if isinstance(result.response, BaseException)
                    else IngestSummaryResult(
                        document_uri=result.document_uri,
                        num_elements=len(result.response),
                    )
                    for result in batch["results"]
                ]
            }

        dataset = (
            ray.data.from_items(list(documents))
            .map_batches(
                fn=_parse,
                batch_size=self.cpu_batch_size,
                num_cpus=1,
                memory=self.cpu_memory,
                zero_copy_batch=True,
            )
            .map_batches(
                fn=_remove,
                batch_size=self.io_batch_size,
                num_cpus=0,
                memory=self.io_memory,
            )
            .map_batches(
                fn=_insert,
                batch_size=self.io_batch_size,
                num_cpus=0,
                memory=self.io_memory,
            )
            .map_batches(
                fn=_summarize,
                batch_size=self.io_batch_size,
                num_cpus=0,
                memory=self.io_memory,
                zero_copy_batch=True,
            )
        )
        return IngestExecutionResult(
            successful=[data["results"] for data in dataset.filter(lambda data: not data["results"].error).take_all()],
            failed=[data["results"] for data in dataset.filter(lambda data: data["results"].error).take_all()],
        )
