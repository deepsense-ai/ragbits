import pytest
from dotenv import load_dotenv

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.providers.base import DocumentTypeNotSupportedError
from ragbits.document_search.ingestion.providers.unstructured import (
    DEFAULT_PARTITION_KWARGS,
    UNSTRUCTURED_API_KEY_ENV,
    UNSTRUCTURED_API_URL_ENV,
    UnstructuredProvider,
)

from ..helpers import env_vars_not_set

load_dotenv()


@pytest.mark.parametrize("document_type", UnstructuredProvider.SUPPORTED_DOCUMENT_TYPES)
def test_unsupported_provider_validates_supported_document_types_passes(document_type: DocumentType):
    UnstructuredProvider().validate_document_type(document_type)


def test_unsupported_provider_validates_supported_document_types_fails():
    with pytest.raises(DocumentTypeNotSupportedError) as err:
        UnstructuredProvider().validate_document_type(DocumentType.UNKNOWN)

    assert "Document type unknown is not supported by the UnstructuredProvider" in str(err.value)


async def test_unstructured_provider_raises_value_error_when_api_key_not_set():
    with pytest.raises(ValueError) as err:
        await UnstructuredProvider().process(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
        )

    assert f"{UNSTRUCTURED_API_KEY_ENV} environment variable is not set" in str(err.value)


async def test_unstructured_provider_raises_value_error_when_api_url_not_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(UNSTRUCTURED_API_KEY_ENV, "dummy_key")
    with pytest.raises(ValueError) as err:
        await UnstructuredProvider().process(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
        )

    assert f"{UNSTRUCTURED_API_URL_ENV} environment variable is not set" in str(err.value)


@pytest.mark.skipif(
    env_vars_not_set([UNSTRUCTURED_API_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
    reason="Unstructured API environment variables not set",
)
async def test_unstructured_provider_document_with_default_partition_kwargs():
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
    unstructured_provider = UnstructuredProvider()
    elements = await unstructured_provider.process(document_meta)

    assert unstructured_provider.partition_kwargs == DEFAULT_PARTITION_KWARGS
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George."


@pytest.mark.skipif(
    env_vars_not_set([UNSTRUCTURED_API_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
    reason="Unstructured API environment variables not set",
)
async def test_unstructured_provider_document_with_custom_partition_kwargs():
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
    partition_kwargs = {"languages": ["pl"], "strategy": "fast"}
    unstructured_provider = UnstructuredProvider(partition_kwargs=partition_kwargs)
    elements = await unstructured_provider.process(document_meta)

    assert unstructured_provider.partition_kwargs == partition_kwargs
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George."
