from pathlib import Path

import pytest

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers.base import TextDocumentParser
from ragbits.document_search.ingestion.parsers.exceptions import ParserNotFoundError
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.strategies.base import IngestStrategy
from ragbits.document_search.ingestion.strategies.batched import BatchedIngestStrategy
from ragbits.document_search.ingestion.strategies.ray import RayDistributedIngestStrategy
from ragbits.document_search.ingestion.strategies.sequential import SequentialIngestStrategy


@pytest.fixture(
    name="ingest_strategy",
    params=[
        SequentialIngestStrategy(num_retries=0),
        BatchedIngestStrategy(batch_size=2, num_retries=0),
        RayDistributedIngestStrategy(batch_size=1, enrich_batch_size=2, index_batch_size=2, num_retries=0),
    ],
    ids=["SequentialIngestStrategy", "BatchedIngestStrategy", "RayDistributedIngestStrategy"],
)
def ingest_strategy_fixture(request: pytest.FixtureRequest) -> IngestStrategy:
    return request.param


async def test_ingest_strategy_call(ingest_strategy: IngestStrategy) -> None:
    documents = [
        DocumentMeta.from_literal("Name of Peppa's brother is George"),
        DocumentMeta.from_literal("Name of Peppa's mother is Mummy Pig"),
        DocumentMeta.from_literal("Name of Peppa's father is Daddy Pig"),
        DocumentMeta.from_literal("Name of Peppa's grandfather is Grandpa Pig"),
        DocumentMeta.from_literal("Name of Peppa's grandmother is Granny Pig"),
    ]
    vector_store = InMemoryVectorStore(embedder=NoopEmbedder())
    parser_router = DocumentParserRouter({DocumentType.TXT: TextDocumentParser()})
    enricher_router = ElementEnricherRouter()

    results = await ingest_strategy(
        documents=documents,
        vector_store=vector_store,
        parser_router=parser_router,
        enricher_router=enricher_router,
    )

    assert len(results.successful) == 5
    assert len(results.failed) == 0


async def test_ingest_strategy_call_fail(ingest_strategy: IngestStrategy) -> None:
    documents = [
        DocumentMeta.from_literal("Name of Peppa's brother is George"),
        DocumentMeta.from_literal("Name of Peppa's mother is Mummy Pig"),
        DocumentMeta.from_literal("Name of Peppa's father is Daddy Pig"),
        DocumentMeta.from_local_path(Path(__file__).parent.parent / "assets" / "img" / "transformers_paper_page.png"),
        DocumentMeta.from_local_path(Path(__file__).parent.parent / "assets" / "pdf" / "transformers_paper_page.pdf"),
    ]
    vector_store = InMemoryVectorStore(embedder=NoopEmbedder())
    parser_router = DocumentParserRouter()
    parser_router._parsers = {DocumentType.TXT: TextDocumentParser()}
    enricher_router = ElementEnricherRouter()

    results = await ingest_strategy(
        documents=documents,
        vector_store=vector_store,
        parser_router=parser_router,
        enricher_router=enricher_router,
    )

    assert len(results.successful) == 3
    assert len(results.failed) == 2

    for result in results.successful:
        assert result.num_elements == 1
        assert result.error is None

    for result in results.failed:
        assert result.num_elements == 0
        assert result.error is not None
        assert result.error.type == ParserNotFoundError
        assert result.error.stacktrace.startswith("Traceback")
        assert "No parser found for the document type" in result.error.stacktrace
        assert "No parser found for the document type" in result.error.message
