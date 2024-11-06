from argparse import Namespace
from collections.abc import Sequence
from unittest.mock import patch

import pytest

from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker


class CustomReranker(Reranker):
    """
    Custom implementation of Reranker for testing.
    """

    async def rerank(  # noqa: PLR6301
        self, elements: Sequence[Element], query: str, options: RerankerOptions | None = None
    ) -> Sequence[Element]:
        return elements


def test_custom_reranker_from_config() -> None:
    with pytest.raises(NotImplementedError) as exc_info:
        CustomReranker.from_config({})

    assert "Cannot create class CustomReranker from config" in str(exc_info.value)


def test_litellm_reranker_from_config() -> None:
    reranker = LiteLLMReranker.from_config(
        {
            "model": "test-provder/test-model",
            "default_options": {
                "top_n": 2,
                "max_chunks_per_doc": None,
            },
        }
    )

    assert reranker.model == "test-provder/test-model"
    assert reranker._default_options == RerankerOptions(top_n=2, max_chunks_per_doc=None)


async def test_litellm_reranker_rerank() -> None:
    options = RerankerOptions(top_n=2, max_chunks_per_doc=None)
    reranker = LiteLLMReranker(
        model="test-provder/test-model",
        default_options=options,
    )
    documents = [
        DocumentMeta.create_text_document_from_literal("Mock document Element 1"),
        DocumentMeta.create_text_document_from_literal("Mock document Element 2"),
        DocumentMeta.create_text_document_from_literal("Mock document Element 3"),
    ]
    elements = [
        TextElement(content="Element 1", document_meta=documents[0]),
        TextElement(content="Element 2", document_meta=documents[1]),
        TextElement(content="Element 3", document_meta=documents[2]),
    ]
    reranked_elements = [
        TextElement(content="Element 2", document_meta=documents[1]),
        TextElement(content="Element 3", document_meta=documents[2]),
        TextElement(content="Element 1", document_meta=documents[0]),
    ]
    reranker_output = Namespace(results=[{"index": 1}, {"index": 2}, {"index": 0}])
    query = "Test query"

    with patch(
        "ragbits.document_search.retrieval.rerankers.litellm.litellm.arerank", return_value=reranker_output
    ) as mock_arerank:
        results = await reranker.rerank(elements, query)

    assert results == reranked_elements
    mock_arerank.assert_called_once_with(
        model="test-provder/test-model",
        query=query,
        documents=["Element 1", "Element 2", "Element 3"],
        top_n=2,
        max_chunks_per_doc=None,
    )
