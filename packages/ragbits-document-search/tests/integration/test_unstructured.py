from pathlib import Path

import pytest

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.unstructured import (
    DEFAULT_PARTITION_KWARGS,
    UNSTRUCTURED_API_KEY_ENV,
    UNSTRUCTURED_SERVER_URL_ENV,
    UnstructuredProvider,
)

from ..helpers import env_vars_not_set


@pytest.mark.parametrize(
    "config",
    [
        {},
        pytest.param(
            {DocumentType.TXT: UnstructuredProvider(use_api=True)},
            marks=pytest.mark.skipif(
                env_vars_not_set([UNSTRUCTURED_SERVER_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
                reason="Unstructured API environment variables not set",
            ),
        ),
    ],
)
async def test_document_processor_processes_text_document_with_unstructured_provider(config):
    document_processor = DocumentProcessorRouter.from_config(config)
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")

    elements = await document_processor.get_provider(document_meta).process(document_meta)

    assert isinstance(document_processor._providers[DocumentType.TXT], UnstructuredProvider)
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George."


@pytest.mark.skipif(
    env_vars_not_set([UNSTRUCTURED_SERVER_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
    reason="Unstructured API environment variables not set",
)
async def test_document_processor_processes_md_document_with_unstructured_provider():
    document_processor = DocumentProcessorRouter.from_config()
    document_meta = DocumentMeta.from_local_path(Path(__file__).parent / "test_file.md")

    elements = await document_processor.get_provider(document_meta).process(document_meta)

    assert len(elements) == 1
    assert elements[0].content == "Ragbits\n\nRepository for internal experiment with our upcoming LLM framework."


@pytest.mark.parametrize(
    "use_api",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                env_vars_not_set([UNSTRUCTURED_SERVER_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
                reason="Unstructured API environment variables not set",
            ),
        ),
    ],
)
async def test_unstructured_provider_document_with_default_partition_kwargs(use_api):
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
    unstructured_provider = UnstructuredProvider(use_api=use_api)
    elements = await unstructured_provider.process(document_meta)

    assert unstructured_provider.partition_kwargs == DEFAULT_PARTITION_KWARGS
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George."


@pytest.mark.parametrize(
    "use_api",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                env_vars_not_set([UNSTRUCTURED_SERVER_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
                reason="Unstructured API environment variables not set",
            ),
        ),
    ],
)
async def test_unstructured_provider_document_with_custom_partition_kwargs(use_api):
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")
    partition_kwargs = {"languages": ["pl"], "strategy": "fast"}
    unstructured_provider = UnstructuredProvider(use_api=use_api, partition_kwargs=partition_kwargs)
    elements = await unstructured_provider.process(document_meta)

    assert unstructured_provider.partition_kwargs == partition_kwargs
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George."
