import pytest

from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.ingestion.parsers.base import (
    DocumentParser,
    TextDocumentParser,
)
from ragbits.document_search.ingestion.parsers.exceptions import ParserDocumentNotSupportedError
from ragbits.document_search.ingestion.parsers.unstructured import UnstructuredDocumentParser


@pytest.mark.parametrize("document_type", UnstructuredDocumentParser.supported_document_types)
def test_parser_validates_supported_document_types_passes(document_type: DocumentType) -> None:
    UnstructuredDocumentParser().validate_document_type(document_type)


def test_parser_validates_supported_document_types_fails() -> None:
    with pytest.raises(ParserDocumentNotSupportedError) as err:
        UnstructuredDocumentParser().validate_document_type(DocumentType.UNKNOWN)
    assert "Document type unknown is not supported by the UnstructuredDocumentParser" in str(err.value)


def test_subclass_from_config() -> None:
    config = ObjectContructionConfig.model_validate(
        {"type": "ragbits.document_search.ingestion.parsers:TextDocumentParser"}
    )
    parser = DocumentParser.subclass_from_config(config)
    assert isinstance(parser, TextDocumentParser)


def test_subclass_from_config_default_path() -> None:
    config = ObjectContructionConfig.model_validate({"type": "TextDocumentParser"})
    parser = DocumentParser.subclass_from_config(config)
    assert isinstance(parser, TextDocumentParser)
