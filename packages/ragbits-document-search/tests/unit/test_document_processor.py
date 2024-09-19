from pathlib import Path

import pytest

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.document_processor import DocumentProcessor
from ragbits.document_search.ingestion.providers.dummy import DummyProvider
from ragbits.document_search.ingestion.providers.unstructured import (
    UNSTRUCTURED_API_KEY_ENV,
    UNSTRUCTURED_API_URL_ENV,
    UnstructuredProvider,
)

from ..helpers import env_vars_not_set


async def test_document_processor_processes_text_document_with_dummy_provider():
    providers_config = {DocumentType.TXT: DummyProvider()}
    document_processor = DocumentProcessor.from_config(providers_config)
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")

    elements = await document_processor.process(document_meta)

    assert isinstance(document_processor._providers[DocumentType.TXT], DummyProvider)
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George"


@pytest.mark.skipif(
    env_vars_not_set([UNSTRUCTURED_API_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
    reason="Unstructured API environment variables not set",
)
async def test_document_processor_processes_text_document_with_unstructured_provider():
    document_processor = DocumentProcessor.from_config()
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George.")

    elements = await document_processor.process(document_meta)

    assert isinstance(document_processor._providers[DocumentType.TXT], UnstructuredProvider)
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George"


@pytest.mark.skipif(
    env_vars_not_set([UNSTRUCTURED_API_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
    reason="Unstructured API environment variables not set",
)
async def test_document_processor_processes_md_document_with_unstructured_provider():
    document_processor = DocumentProcessor.from_config()
    document_meta = DocumentMeta.from_local_path(Path(__file__).parent.parent.parent.parent.parent / "README.md")

    elements = await document_processor.process(document_meta)

    assert len(elements) > 0
    assert elements[0].content == "Ragbits"
