import asyncio
from collections.abc import Iterable

from ragbits.core.sources.base import Source
from ragbits.core.utils.decorators import requires_dependencies
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.strategies.base import (
    IngestDocumentResult,
    IngestExecutionResult,
)
from ragbits.document_search.ingestion.strategies.batched import BatchedIngestStrategy, IngestTaskResult


class RayDistributedIngestStrategy(BatchedIngestStrategy):
    """
    Ingest strategy that processes documents on a cluster, using Ray.
    """

    def __init__(
        self,
        batch_size: int = 1,
        enrich_batch_size: int | None = None,
        index_batch_size: int | None = None,
        parse_memory: float | None = None,
        processing_memory: float | None = None,
        num_retries: int = 3,
        backoff_multiplier: int = 1,
        backoff_max: int = 60,
    ) -> None:
        """
        Initialize the RayDistributedIngestStrategy instance.

        Args:
            batch_size: The batch size for parsing documents.
            enrich_batch_size: The batch size for enriching elements.
                Describes the maximum number of document elements to enrich at once.
                If None, all elements are enriched at once.
            index_batch_size: The batch size for indexing elements.
                Describes the maximum number of document elements to index at once.
                If None, all elements are indexed at once.
            parse_memory: The heap memory in bytes to reserve for each parallel parsing tasks.
            processing_memory: The heap memory in bytes to reserve for each parallel elements processing tasks.
            num_retries: The number of retries per document ingest task error.
            backoff_multiplier: The base delay multiplier for exponential backoff (in seconds).
            backoff_max: The maximum allowed delay (in seconds) between retries.
        """
        super().__init__(
            batch_size=batch_size,
            enrich_batch_size=enrich_batch_size,
            index_batch_size=index_batch_size,
            num_retries=num_retries,
            backoff_multiplier=backoff_multiplier,
            backoff_max=backoff_max,
        )
        self.parse_memory = parse_memory
        self.processing_memory = processing_memory

    @requires_dependencies(["ray.data"], "ray")
    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        parser_router: DocumentParserRouter,
        enricher_router: ElementEnricherRouter,
    ) -> IngestExecutionResult:
        """
        Ingest documents in parallel in batches.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            parser_router: The document parser router to use.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The ingest execution result.
        """
        import ray

        # Parse documents
        parse_results = ray.data.from_items(list(documents)).map_batches(
            fn=lambda batch: {"results": asyncio.run(self._parse_batch(batch["item"], parser_router))},
            batch_size=self.batch_size,
            num_cpus=1,
            memory=self.parse_memory,
            zero_copy_batch=True,
        )

        # Split documents into successful and failed
        successfully_parsed = parse_results.filter(lambda data: isinstance(data["results"], IngestTaskResult))
        failed_parsed = parse_results.filter(lambda data: isinstance(data["results"], IngestDocumentResult))

        # Further split valid documents into to enrich and ready
        to_enrich = successfully_parsed.filter(
            lambda data: any(type(element) in enricher_router for element in data["results"].elements)
        )
        ready_parsed = successfully_parsed.filter(
            lambda data: not any(type(element) in enricher_router for element in data["results"].elements)
        )

        # Enrich documents
        enrich_results = to_enrich.map_batches(
            fn=lambda batch: {"results": asyncio.run(self._enrich_batch(batch["results"], enricher_router))},
            batch_size=self.batch_size,
            num_cpus=0,
            memory=self.processing_memory,
        )

        # Split enriched documents into successful and failed
        successfully_enriched = enrich_results.filter(lambda data: isinstance(data["results"], IngestTaskResult))
        failed_enriched = enrich_results.filter(lambda data: isinstance(data["results"], IngestDocumentResult))

        # Combine ready documents with successfully enriched documents for indexing
        to_index = ready_parsed.union(successfully_enriched)

        # Index the combined documents
        index_results = to_index.map_batches(
            fn=lambda batch: {"results": asyncio.run(self._index_batch(batch["results"], vector_store))},
            batch_size=self.batch_size,
            num_cpus=0,
            memory=self.processing_memory,
        )

        # Split indexed documents into successful and failed
        successfully_indexed = index_results.filter(lambda data: not data["results"].error)
        failed_indexed = index_results.filter(lambda data: data["results"].error)

        # Combine all failed documents
        all_failed = failed_parsed.union(failed_enriched, failed_indexed)

        # Return the final result
        return IngestExecutionResult(
            successful=[data["results"] for data in successfully_indexed.take_all()],
            failed=[data["results"] for data in all_failed.take_all()],
        )
