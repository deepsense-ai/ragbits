import pytest

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import Document, DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.parsers.base import DocumentParser
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.strategies.base import IngestExecutionError


class FailingParser(DocumentParser):
    """A parser that always raises an exception."""

    supported_document_types = {DocumentType.TXT}

    @classmethod
    async def parse(cls, document: Document) -> list[Element]:
        raise ValueError("This parser always fails")


async def test_ingest_fails_on_error():
    # Create a document search instance with a failing parser
    document_search: DocumentSearch = DocumentSearch(
        vector_store=InMemoryVectorStore(embedder=NoopEmbedder()),
        parser_router=DocumentParserRouter({DocumentType.TXT: FailingParser()}),
    )

    # Create a test document
    document = DocumentMeta.from_literal("Test content")

    # Test that ingest raises IngestExecutionError when fail_on_error=True (default)
    with pytest.raises(IngestExecutionError) as exc_info:
        await document_search.ingest([document])

    # Verify the error details
    assert len(exc_info.value.results) == 1
    failed_result = exc_info.value.results[0]
    assert failed_result.document_uri == document.id
    assert failed_result.num_elements == 0
    assert failed_result.error is not None
    assert isinstance(failed_result.error.type, type(ValueError))
    assert failed_result.error.message == "This parser always fails"


async def test_ingest_returns_errors_when_fail_on_error_false():
    # Create a document search instance with a failing parser
    document_search: DocumentSearch = DocumentSearch(
        vector_store=InMemoryVectorStore(embedder=NoopEmbedder()),
        parser_router=DocumentParserRouter({DocumentType.TXT: FailingParser()}),
    )

    # Create a test document
    document = DocumentMeta.from_literal("Test content")

    # Test that ingest returns errors when fail_on_error=False
    result = await document_search.ingest([document], fail_on_error=False)

    # Verify the result details
    assert len(result.successful) == 0
    assert len(result.failed) == 1
    failed_result = result.failed[0]
    assert failed_result.document_uri == document.id
    assert failed_result.num_elements == 0
    assert failed_result.error is not None
    assert isinstance(failed_result.error.type, type(ValueError))
    assert failed_result.error.message == "This parser always fails"
