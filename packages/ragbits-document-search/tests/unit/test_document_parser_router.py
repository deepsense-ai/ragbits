import pytest

from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.ingestion.parsers.base import ImageDocumentParser, TextDocumentParser
from ragbits.document_search.ingestion.parsers.exceptions import ParserNotFoundError
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.parsers.unstructured import UnstructuredDocumentParser


def test_parser_router_from_config() -> None:
    config = {
        "txt": ObjectConstructionConfig.model_validate(
            {"type": "ragbits.document_search.ingestion.parsers.base:TextDocumentParser"}
        ),
        "png": ObjectConstructionConfig.model_validate(
            {"type": "ragbits.document_search.ingestion.parsers.base:ImageDocumentParser"}
        ),
        "pdf": ObjectConstructionConfig.model_validate(
            {"type": "ragbits.document_search.ingestion.parsers.unstructured:UnstructuredDocumentParser"}
        ),
    }
    router = DocumentParserRouter.from_config(config)

    assert isinstance(router._parsers[DocumentType.TXT], TextDocumentParser)
    assert isinstance(router._parsers[DocumentType.PNG], ImageDocumentParser)
    assert isinstance(router._parsers[DocumentType.PDF], UnstructuredDocumentParser)


def test_parser_router_get() -> None:
    parser = TextDocumentParser()
    parser_router = DocumentParserRouter({DocumentType.TXT: parser})

    assert parser_router.get(DocumentType.TXT) is parser


def test_parser_router_get_raises_when_no_parser_found() -> None:
    parser_router = DocumentParserRouter()
    parser_router._parsers = {DocumentType.TXT: TextDocumentParser()}

    with pytest.raises(ParserNotFoundError) as exc:
        parser_router.get(DocumentType.PDF)

    assert exc.value.message == f"No parser found for the document type {DocumentType.PDF}"
    assert exc.value.document_type == DocumentType.PDF
