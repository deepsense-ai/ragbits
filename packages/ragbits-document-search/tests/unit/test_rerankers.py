from pathlib import Path

import pytest

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.documents.sources import LocalFileSource
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker


@pytest.fixture
def mock_litellm_response(monkeypatch):
    class MockResponse:
        results = [{"index": 1}, {"index": 0}]

    async def mock_rerank(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("ragbits.document_search.retrieval.rerankers.litellm.litellm.arerank", mock_rerank)


@pytest.fixture
def reranker():
    return LiteLLMReranker(
        model="test_provder/test_model",
        top_n=2,
        return_documents=True,
        rank_fields=["content"],
        max_chunks_per_doc=1,
    )


@pytest.fixture
def mock_document_meta():
    return DocumentMeta(document_type=DocumentType.TXT, source=LocalFileSource(path=Path("test.txt")))


@pytest.fixture
def mock_custom_element(mock_document_meta):
    class CustomElement(Element):
        def get_key(self):
            return "test_key"

    return CustomElement(element_type="test_type", document_meta=mock_document_meta)


async def test_rerank_success(reranker, mock_litellm_response, mock_document_meta):
    chunks = [
        TextElement(content="chunk1", document_meta=mock_document_meta),
        TextElement(content="chunk2", document_meta=mock_document_meta),
    ]
    query = "test query"

    reranked_chunks = await reranker.rerank(chunks, query)

    assert reranked_chunks[0].content == "chunk2"
    assert reranked_chunks[1].content == "chunk1"


async def test_rerank_invalid_chunks(reranker, mock_custom_element):
    chunks = [mock_custom_element]
    query = "test query"

    with pytest.raises(ValueError, match="All chunks must be TextElement instances"):
        await reranker.rerank(chunks, query)
