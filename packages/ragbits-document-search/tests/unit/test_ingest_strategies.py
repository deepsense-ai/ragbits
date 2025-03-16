import pytest

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.dummy import DummyProvider
from ragbits.document_search.ingestion.strategies.batched import BatchedIngestStrategy
from ragbits.document_search.ingestion.strategies.ray import RayDistributedIngestStrategy
from ragbits.document_search.ingestion.strategies.sequential import SequentialIngestStrategy


@pytest.fixture(name="documents")
def documents_fixture() -> list[DocumentMeta]:
    return [
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's mother is Mummy Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's father is Daddy Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's grandfather is Grandpa Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's grandmother is Granny Pig"),
    ]


async def test_sequential_strategy(documents: list[DocumentMeta]):
    embedder = NoopEmbedder()
    vector_store = InMemoryVectorStore(embedder=embedder)
    parser_router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})
    strategy = SequentialIngestStrategy()

    results = await strategy(
        documents=documents,
        vector_store=vector_store,
        parser_router=parser_router,
        enricher_router={},
    )

    assert len(results.successful) == 5


async def test_batched_strategy(documents: list[DocumentMeta]):
    embedder = NoopEmbedder()
    vector_store = InMemoryVectorStore(embedder=embedder)
    parser_router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})
    strategy = BatchedIngestStrategy(batch_size=2)

    results = await strategy(
        documents=documents,
        vector_store=vector_store,
        parser_router=parser_router,
        enricher_router={},
    )

    assert len(results.successful) == 5


async def test_distributed_strategy(documents: list[DocumentMeta]):
    embedder = NoopEmbedder()
    vector_store = InMemoryVectorStore(embedder=embedder)
    parser_router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})
    strategy = RayDistributedIngestStrategy()

    results = await strategy(
        documents=documents,
        vector_store=vector_store,
        parser_router=parser_router,
        enricher_router={},
    )

    assert len(results.successful) == 5
