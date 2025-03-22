import pytest

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers.base import TextDocumentParser
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
        RayDistributedIngestStrategy(cpu_batch_size=1, io_batch_size=2, num_retries=0),
    ],
    ids=["SequentialIngestStrategy", "BatchedIngestStrategy", "RayDistributedIngestStrategy"],
)
def ingest_strategy_fixture(request: pytest.FixtureRequest) -> IngestStrategy:
    return request.param


@pytest.fixture(name="documents")
def documents_fixture() -> list[DocumentMeta]:
    return [
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's mother is Mummy Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's father is Daddy Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's grandfather is Grandpa Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's grandmother is Granny Pig"),
    ]


async def test_ingest_strategy_call(ingest_strategy: IngestStrategy, documents: list[DocumentMeta]) -> None:
    vector_store = InMemoryVectorStore(embedder=NoopEmbedder())
    parser_router = DocumentParserRouter({DocumentType.TXT: TextDocumentParser()})
    enricher_router = ElementEnricherRouter()

    results = await ingest_strategy(
        documents=documents,
        vector_store=vector_store,
        parser_router=parser_router,
        enricher_router=enricher_router,
    )

    assert len(results.successful) == len(documents)
    assert len(results.failed) == 0
