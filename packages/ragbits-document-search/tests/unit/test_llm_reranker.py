import math
from collections.abc import Sequence
from unittest.mock import AsyncMock, Mock

import pytest

from ragbits.core.llms.base import LLMResponseWithMetadata
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.retrieval.rerankers.base import Reranker
from ragbits.document_search.retrieval.rerankers.llm import LLMReranker, LLMRerankerOptions, RerankerPrompt


@pytest.fixture
def mock_llm() -> AsyncMock:
    mock = AsyncMock(spec=LiteLLM)
    mock.model_name = "gpt-3.5-turbo"
    mock.default_options = LiteLLMOptions()
    mock.generate_with_metadata.side_effect = [
        LLMResponseWithMetadata(content="Yes", metadata={"logprobs": [{"logprob": math.log(0.9)}]}),  # High relevance
        LLMResponseWithMetadata(content="No", metadata={"logprobs": [{"logprob": math.log(0.6)}]}),  # Low relevance
        LLMResponseWithMetadata(content="Yes", metadata={"logprobs": [{"logprob": math.log(0.6)}]}),  # Medium relevance
    ]
    return mock


@pytest.fixture
def sample_elements() -> Sequence[Sequence[TextElement]]:
    return [
        [
            TextElement(
                content="This is a relevant document about Python programming", document_meta=Mock(spec=DocumentMeta)
            )
        ],
        [
            TextElement(content="This document is about cooking recipes", document_meta=Mock(spec=DocumentMeta)),
            TextElement(
                content="Information about Python frameworks and libraries", document_meta=Mock(spec=DocumentMeta)
            ),
        ],
    ]


async def test_llm_reranker_from_config() -> None:
    reranker = LLMReranker.from_config(
        {
            "llm": {
                "type": "ragbits.core.llms.litellm:LiteLLM",
                "config": {
                    "model_name": "gpt-4o",
                },
            },
            "default_options": {
                "top_n": 2,
            },
        }
    )

    assert reranker.default_options == LLMRerankerOptions(top_n=2)
    assert reranker._llm.model_name == "gpt-4o"


def test_llm_reranker_subclass_from_config() -> None:
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rerankers.llm:LLMReranker",
            "config": {
                "llm": {
                    "type": "ragbits.core.llms.litellm:LiteLLM",
                    "config": {
                        "model_name": "gpt-4o",
                    },
                },
                "prompt": "ragbits.document_search.retrieval.rerankers.llm:RerankerPrompt",
                "default_options": {
                    "top_n": 12,
                },
            },
        }
    )
    reranker: Reranker = Reranker.subclass_from_config(config)

    assert isinstance(reranker, LLMReranker)
    assert isinstance(reranker._llm, LiteLLM)
    assert isinstance(reranker.default_options, LLMRerankerOptions)
    assert reranker._prompt == RerankerPrompt
    assert reranker._llm.model_name == "gpt-4o"
    assert reranker.default_options.top_n == 12


async def test_llm_reranker_rerank(mock_llm: AsyncMock, sample_elements: Sequence[Sequence[TextElement]]) -> None:
    custom_top_n = 2
    custom_options = LLMRerankerOptions(top_n=custom_top_n)
    reranker = LLMReranker(llm=mock_llm)
    result = await reranker.rerank(
        elements=sample_elements,
        query="Python programming",
        options=custom_options,
    )

    # Check that the correct number of elements is returned
    assert len(result) == custom_top_n

    # Verify the reranking worked correctly (highest score first)
    flat_elements = [element for item in sample_elements for element in item]
    assert result[0] == flat_elements[0]  # First element had the highest score
    assert result[1] == flat_elements[2]  # Third element had the second-highest score
