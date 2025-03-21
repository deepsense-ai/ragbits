import os
from unittest.mock import patch

import pytest

from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.parsers.base import DocumentParser, DocumentTypeNotSupportedError
from ragbits.document_search.ingestion.parsers.dummy import DummyProvider
from ragbits.document_search.ingestion.parsers.unstructured import UnstructuredDocumentParser


@pytest.mark.parametrize("document_type", UnstructuredDocumentParser.supported_document_types)
def test_unsupported_provider_validates_supported_document_types_passes(document_type: DocumentType):
    UnstructuredDocumentParser().validate_document_type(document_type)


def test_unsupported_provider_validates_supported_document_types_fails():
    with pytest.raises(DocumentTypeNotSupportedError) as err:
        UnstructuredDocumentParser().validate_document_type(DocumentType.UNKNOWN)

    assert "Document type unknown is not supported by the UnstructuredDocumentParser" in str(err.value)


@patch.dict(os.environ, {}, clear=True)
async def test_unstructured_provider_raises_value_error_when_api_key_not_set():
    with pytest.raises(ValueError) as err:
        await UnstructuredDocumentParser(use_api=True).parse(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
        )

    assert str(err.value) == "Either pass api_key argument or set the UNSTRUCTURED_API_KEY environment variable"


@patch.dict(os.environ, {}, clear=True)
async def test_unstructured_provider_raises_value_error_when_server_url_not_set():
    with pytest.raises(ValueError) as err:
        await UnstructuredDocumentParser(api_key="api_key", use_api=True).parse(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
        )

    assert str(err.value) == "Either pass api_server argument or set the UNSTRUCTURED_SERVER_URL environment variable"


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate({"type": "ragbits.document_search.ingestion.parsers:DummyProvider"})
    parser = DocumentParser.subclass_from_config(config)
    assert isinstance(parser, DummyProvider)


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "DummyProvider"})
    parser = DocumentParser.subclass_from_config(config)
    assert isinstance(parser, DummyProvider)
