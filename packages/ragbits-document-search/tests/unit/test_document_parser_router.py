import pytest

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.parsers.dummy import DummyProvider
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter


async def test_parser_router():
    parser_router = DocumentParserRouter({DocumentType.TXT: DummyProvider()})

    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")

    parser = parser_router.get(document_meta)

    assert isinstance(parser, DummyProvider)


async def test_parser_router_raises_when_no_parser_found():
    parser_router = DocumentParserRouter()
    parser_router._parsers = {DocumentType.TXT: DummyProvider()}

    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")

    document_meta.document_type = DocumentType.PDF

    with pytest.raises(ValueError) as err:
        _ = parser_router.get(document_meta)

    assert str(err.value) == f"No parser found for the document type {DocumentType.PDF}"
