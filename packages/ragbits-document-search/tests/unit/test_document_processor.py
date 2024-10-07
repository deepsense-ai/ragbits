import pytest

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.dummy import DummyProvider


async def test_document_processor_router():
    document_processor_router = DocumentProcessorRouter.from_config({DocumentType.TXT: DummyProvider()})

    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")

    document_processor = document_processor_router.get_provider(document_meta)

    assert isinstance(document_processor, DummyProvider)


async def test_document_processor_router_raises_when_no_provider_found():
    document_processor_router = DocumentProcessorRouter.from_config()
    document_processor_router._providers = {DocumentType.TXT: DummyProvider()}

    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")

    document_meta.document_type = DocumentType.PDF

    with pytest.raises(ValueError) as err:
        _ = document_processor_router.get_provider(document_meta)

    assert str(err.value) == f"No provider found for the document type {DocumentType.PDF}"
