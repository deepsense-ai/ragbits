import pytest

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
    router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})
    strategy = SequentialIngestStrategy()
    elements = await strategy.process_documents(documents, router)
    assert len(elements) == 5


async def test_batched_strategy(documents: list[DocumentMeta]):
    router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})
    strategy = BatchedIngestStrategy(batch_size=2)
    elements = await strategy.process_documents(documents, router)
    assert len(elements) == 5


async def test_distributed_strategy(documents: list[DocumentMeta]):
    router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})
    strategy = RayDistributedIngestStrategy()
    elements = await strategy.process_documents(documents, router)
    assert len(elements) == 5
