from argparse import Namespace
from collections.abc import Sequence
from unittest.mock import Mock, patch

from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.retrieval.rerankers.answerai import AnswerAIReranker
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker, LiteLLMRerankerOptions
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker
from ragbits.document_search.retrieval.rerankers.rrf import ReciprocalRankFusionReranker


class CustomReranker(Reranker):
    """
    Custom implementation of Reranker for testing.
    """

    options_cls = RerankerOptions

    async def rerank(  # noqa: PLR6301
        self, elements: Sequence[Sequence[Element]], query: str, options: RerankerOptions | None = None
    ) -> Sequence[Element]:
        return elements[0]


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
    assert reranker.default_options == LiteLLMRerankerOptions(top_n=2, max_chunks_per_doc=None)


def test_aswerdotai_reranker_from_config() -> None:
    reranker = AnswerAIReranker.from_config(
        {
            "model": "cross-encoder",
            "default_options": {
                "top_n": 2,
            },
        }
    )

    assert reranker.model == "cross-encoder"  # type: ignore
    assert reranker.default_options == RerankerOptions(top_n=2)


def test_reciprocal_rank_fusion_reranker_from_config() -> None:
    reranker = ReciprocalRankFusionReranker.from_config(
        {
            "default_options": {
                "top_n": 2,
            },
        }
    )

    assert reranker.default_options == RerankerOptions(top_n=2)


async def test_litellm_reranker_rerank() -> None:
    options = LiteLLMRerankerOptions(top_n=2, max_chunks_per_doc=None)
    reranker = LiteLLMReranker(
        model="test-provder/test-model",
        default_options=options,
    )
    documents = [
        DocumentMeta.from_literal("Mock document Element 1"),
        DocumentMeta.from_literal("Mock document Element 2"),
        DocumentMeta.from_literal("Mock document Element 3"),
    ]
    elements = [
        [
            TextElement(content="Element 1", document_meta=documents[0]),
            TextElement(content="Element 2", document_meta=documents[1]),
            TextElement(content="Element 3", document_meta=documents[2]),
        ]
    ]
    reranked_elements = [
        TextElement(content="Element 2", document_meta=documents[1], score=0.9),
        TextElement(content="Element 3", document_meta=documents[2], score=0.6),
        TextElement(content="Element 1", document_meta=documents[0], score=0.4),
    ]
    reranker_output = Namespace(
        results=[
            {"index": 1, "relevance_score": 0.9},
            {"index": 2, "relevance_score": 0.6},
            {"index": 0, "relevance_score": 0.4},
        ]
    )
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


async def test_answerdotai_reranker_rerank() -> None:
    reranker = AnswerAIReranker(
        model="cross-encoder",
    )
    documents = [
        DocumentMeta.from_literal("Mock document Element 1"),
        DocumentMeta.from_literal("Mock document Element 2"),
        DocumentMeta.from_literal("Mock document Element 3"),
    ]
    elements = [
        [
            TextElement(content="Element 1", document_meta=documents[0]),
            TextElement(content="Element 2", document_meta=documents[1]),
            TextElement(content="Element 3", document_meta=documents[2]),
        ]
    ]
    reranked_elements = [
        TextElement(content="Element 1", document_meta=documents[0], score=0.9),
        TextElement(content="Element 3", document_meta=documents[2], score=0.5),
    ]
    query = "Test query"

    mock_ranker_instance = Mock()
    mock_ranker_instance.rank.return_value = [
        Namespace(document=Namespace(doc_id=0), score=0.9),  # Corresponds to Element 1
        Namespace(document=Namespace(doc_id=2), score=0.5),  # Corresponds to Element 3
    ]

    reranker.ranker = mock_ranker_instance
    results = await reranker.rerank(elements, query)
    assert results == reranked_elements

    mock_ranker_instance.rank.assert_called_once_with(
        query=query,
        docs=["Element 1", "Element 2", "Element 3"],
    )


async def test_reciprocal_rank_fusion_reranker_rerank() -> None:
    options = RerankerOptions(top_n=2)
    reranker = ReciprocalRankFusionReranker(
        default_options=options,
    )
    documents = [
        DocumentMeta.from_literal("Mock document Element 1"),
        DocumentMeta.from_literal("Mock document Element 2"),
        DocumentMeta.from_literal("Mock document Element 3"),
    ]
    elements = [
        [
            TextElement(content="Element 1", document_meta=documents[0]),
            TextElement(content="Element 2", document_meta=documents[1]),
            TextElement(content="Element 3", document_meta=documents[2]),
        ],
        [
            TextElement(content="Element 1", document_meta=documents[0]),
            TextElement(content="Element 2", document_meta=documents[1]),
        ],
        [
            TextElement(content="Element 2", document_meta=documents[1]),
        ],
    ]
    reranked_elements = [
        TextElement(content="Element 2", document_meta=documents[1], score=1.1666666666666665),
        TextElement(content="Element 1", document_meta=documents[0], score=1.0),
    ]
    query = "Test query"

    results = await reranker.rerank(elements, query)

    assert results == reranked_elements


def test_subclass_from_config() -> None:
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rerankers:NoopReranker",
            "config": {
                "default_options": {
                    "top_n": 12,
                },
            },
        }
    )
    reranker: Reranker = Reranker.subclass_from_config(config)
    assert isinstance(reranker, NoopReranker)
    assert isinstance(reranker.default_options, RerankerOptions)
    assert reranker.default_options.top_n == 12


def test_subclass_from_config_default_path() -> None:
    config = ObjectConstructionConfig.model_validate({"type": "NoopReranker"})
    reranker: Reranker = Reranker.subclass_from_config(config)
    assert isinstance(reranker, NoopReranker)


def test_subclass_from_config_litellm() -> None:
    config = ObjectConstructionConfig.model_validate(
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
    assert isinstance(reranker.default_options, LiteLLMRerankerOptions)
    assert reranker.model == "some_model"
    assert reranker.default_options.top_n == 12
    assert reranker.default_options.max_chunks_per_doc == 42
