import pytest

from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.ingestion.parsers.base import TextDocumentParser
from ragbits.document_search.ingestion.parsers.exceptions import ParserNotFoundError
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter


async def test_parser_router() -> None:
    parser = TextDocumentParser()
    parser_router = DocumentParserRouter({DocumentType.TXT: parser})

    assert parser_router.get(DocumentType.TXT) is parser


async def test_parser_router_raises_when_no_parser_found() -> None:
    parser_router = DocumentParserRouter()
    parser_router._parsers = {DocumentType.TXT: TextDocumentParser()}

    with pytest.raises(ParserNotFoundError) as err:
        parser_router.get(DocumentType.PDF)

    assert err.value.message == f"No parser found for the document type {DocumentType.PDF}"
    assert err.value.document_type == DocumentType.PDF
