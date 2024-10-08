import os
from unittest.mock import patch

import pytest

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.providers.base import DocumentTypeNotSupportedError
from ragbits.document_search.ingestion.providers.unstructured import UnstructuredProvider


@pytest.mark.parametrize("document_type", UnstructuredProvider.SUPPORTED_DOCUMENT_TYPES)
def test_unsupported_provider_validates_supported_document_types_passes(document_type: DocumentType):
    UnstructuredProvider().validate_document_type(document_type)


def test_unsupported_provider_validates_supported_document_types_fails():
    with pytest.raises(DocumentTypeNotSupportedError) as err:
        UnstructuredProvider().validate_document_type(DocumentType.UNKNOWN)

    assert "Document type unknown is not supported by the UnstructuredProvider" in str(err.value)


@patch.dict(os.environ, {}, clear=True)
async def test_unstructured_provider_raises_value_error_when_api_key_not_set():
    with pytest.raises(ValueError) as err:
        await UnstructuredProvider().process(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
        )

    assert "Either pass api_key argument or set the UNSTRUCTURED_API_KEY environment variable" == str(err.value)


@patch.dict(os.environ, {}, clear=True)
async def test_unstructured_provider_raises_value_error_when_server_url_not_set():
    with pytest.raises(ValueError) as err:
        await UnstructuredProvider(api_key="api_key").process(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
        )

    assert "Either pass api_server argument or set the UNSTRUCTURED_SERVER_URL environment variable" == str(err.value)
