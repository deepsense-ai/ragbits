from argparse import Namespace
from collections.abc import Sequence
from unittest.mock import patch

from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker


class CustomReranker(Reranker):
    """
    Custom implementation of Reranker for testing.
    """

    options_cls = RerankerOptions

    async def rerank(  # noqa: PLR6301
        self, elements: Sequence[Element], query: str, options: RerankerOptions | None = None
    ) -> Sequence[Element]:
        return elements


def test_custom_reranker_from_config() -> None:
    reranker = CustomReranker.from_config({})
    assert isinstance(reranker, CustomReranker)


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

    assert reranker.model == "test-provder/test-model"  # type: ignore
    assert reranker.default_options == RerankerOptions(top_n=2, max_chunks_per_doc=None)


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


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rerankers:NoopReranker",
            "config": {
                "default_options": {
                    "top_n": 12,
                    "max_chunks_per_doc": 42,
                },
            },
        }
    )
    reranker: Reranker = Reranker.subclass_from_config(config)
    assert isinstance(reranker, NoopReranker)
    assert isinstance(reranker.default_options, RerankerOptions)
    assert reranker.default_options.top_n == 12
    assert reranker.default_options.max_chunks_per_doc == 42


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "NoopReranker"})
    reranker: Reranker = Reranker.subclass_from_config(config)
    assert isinstance(reranker, NoopReranker)


def test_subclass_from_config_llm():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rerankers.litellm:LiteLLMReranker",
            "config": {
                "model": "some_model",
                "default_options": {
                    "top_n": 12,
                    "max_chunks_per_doc": 42,
                },
            },
        }
    )
    reranker: Reranker = Reranker.subclass_from_config(config)
    assert isinstance(reranker, LiteLLMReranker)
    assert isinstance(reranker.default_options, RerankerOptions)
    assert reranker.model == "some_model"
    assert reranker.default_options.top_n == 12
    assert reranker.default_options.max_chunks_per_doc == 42
