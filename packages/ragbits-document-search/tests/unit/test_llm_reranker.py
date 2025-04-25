import math
from collections.abc import Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.core.llms import LiteLLM, LiteLLMOptions
from ragbits.core.llms.exceptions import LLMStatusError
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.retrieval.rerankers.base import RerankerOptions
from ragbits.document_search.retrieval.rerankers.llm_reranker import LLMReranker, RerankerPrompt


@pytest.fixture
def mock_llm() -> AsyncMock:
    mock = AsyncMock(spec=LiteLLM)
    mock.model_name = "gpt-3.5-turbo"
    mock.max_tokens = 20
    return mock


@pytest.fixture
def reranker(mock_llm: LiteLLM) -> LLMReranker:
    return LLMReranker(llm=mock_llm)


@pytest.fixture
def sample_elements() -> Sequence[Sequence[TextElement]]:
    documents = [
        DocumentMeta.create_text_document_from_literal("Mock document Element 1"),
        DocumentMeta.create_text_document_from_literal("Mock document Element 2"),
        DocumentMeta.create_text_document_from_literal("Mock document Element 3"),
    ]

    element1 = TextElement(content="This is a relevant document about Python programming", document_meta=documents[0])
    element2 = TextElement(content="This document is about cooking recipes", document_meta=documents[1])
    element3 = TextElement(content="Information about Python frameworks and libraries", document_meta=documents[2])
    return [[element1], [element2, element3]]


@pytest.fixture
def mock_responses(mock_llm: AsyncMock) -> Sequence[dict[str, Any]]:
    """
    Configure the mock_llm.generate_raw to return a sequence of responses.

    Args:
        mock_llm: The mock LLM object
        responses: List of tuples (answer, logprob) where answer is "Yes" or "No"
                  and logprob is the log probability value
    """
    return [
        {"response": "Yes", "logprobs": [{"logprob": math.log(0.9)}]},  # High relevance
        {"response": "No", "logprobs": [{"logprob": math.log(0.6)}]},  # Low relevance
        {"response": "Yes", "logprobs": [{"logprob": math.log(0.6)}]},  # Medium relevance
    ]


async def test_llm_reranker_from_config() -> None:
    reranker = LLMReranker.from_config(
        {
            "llm": LiteLLM(model_name="test-provider/test-model"),
            "default_options": {
                "top_n": 2,
            },
        }
    )

    assert reranker.default_options == RerankerOptions(top_n=2)
    assert reranker.llm.model_name == "test-provider/test-model"


def test_init_with_custom_options(mock_llm: AsyncMock) -> None:
    custom_prompt = RerankerPrompt(custom_user_prompt="Custom prompt {query} {document}")
    custom_reranker_options = RerankerOptions(top_n=2)
    custom_llm_options = LiteLLMOptions(temperature=0.5, max_tokens=5)

    reranker = LLMReranker(
        llm=mock_llm,
        prompt_template=custom_prompt,
        default_options=custom_reranker_options,
        llm_options=custom_llm_options,
    )

    assert reranker.prompt_template == custom_prompt
    assert reranker.default_options.top_n == 2
    assert reranker.llm_options.temperature == 0.5
    assert mock_llm.max_tokens == 20
    assert reranker.llm_options.max_tokens == 5


def test_init_with_default_options(mock_llm: AsyncMock) -> None:
    reranker = LLMReranker(llm=mock_llm)
    assert reranker.prompt_template.user_prompt.strip() == RerankerPrompt.user_prompt.strip()
    assert reranker.default_options.top_n is None
    assert mock_llm.max_tokens == 20
    assert reranker.llm_options.max_tokens == 1


async def test_rerank_returns_top_n_elements(
    reranker: LLMReranker,
    mock_llm: AsyncMock,
    sample_elements: Sequence[Sequence[TextElement]],
    mock_responses: Sequence[dict[str, Any]],
) -> None:
    # Configure the mock to return different scores
    mock_llm.generate_raw.side_effect = mock_responses
    custom_top_n = 2
    query = "Python programming"
    custom_options = RerankerOptions(top_n=custom_top_n)
    result = await reranker.rerank(
        sample_elements,
        query,
        options=custom_options,
    )

    # Check that the correct number of elements is returned
    assert len(result) == custom_top_n

    # Verify the reranking worked correctly (highest score first)
    flat_elements = [element for item in sample_elements for element in item]
    assert result[0] == flat_elements[0]  # First element had the highest score
    assert result[1] == flat_elements[2]  # Third element had the second-highest score


async def test_score_elements(
    reranker: LLMReranker,
    mock_llm: AsyncMock,
    sample_elements: Sequence[Sequence[TextElement]],
    mock_responses: Sequence[dict[str, Any]],
) -> None:
    mock_llm.generate_raw.side_effect = mock_responses

    elements = [element for sublist in sample_elements for element in sublist]
    query = "Test query"
    scores = await reranker._score_elements(elements, query)

    assert len(scores) == 3
    assert scores[0] == 0.9
    assert scores[1] == 0.4
    assert scores[2] == 0.6


async def test_score_elements_errors(reranker: LLMReranker, mock_llm: AsyncMock) -> None:
    # Make the mock raise an exception
    mock_llm.generate_raw.side_effect = LLMStatusError("Model doesn't support logprobs", status_code=500)

    elements = [
        TextElement(
            content="Test document",
            document_meta=DocumentMeta.create_text_document_from_literal("Mock document Element 1"),
        )
    ]
    query = "Test query"

    with pytest.raises(NotImplementedError) as exc_info:
        await reranker._score_elements(elements, query)

    assert "doesn't support logprobs" in str(exc_info.value)


def test_get_yes_no_token_ids_with_tiktoken(reranker: LLMReranker, mock_llm: AsyncMock) -> None:
    test_model_name = "some_openai_model"
    with (
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.litellm") as mock_litellm,
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.tiktoken") as mock_tiktoken,
    ):
        mock_litellm.get_llm_provider.return_value = [test_model_name]

        mock_encoder = MagicMock()
        mock_encoder.encode.side_effect = lambda token: [123] if token == " Yes" else [456]  # noqa: S105
        mock_tiktoken.encoding_for_model.return_value = mock_encoder
        token_ids = reranker.get_yes_no_token_ids()
        assert token_ids == {123: 1, 456: 1}
        mock_tiktoken.encoding_for_model.assert_called_once_with(test_model_name)


def test_get_yes_no_token_ids_with_autotokenizer(reranker: LLMReranker, mock_llm: AsyncMock) -> None:
    test_model_name = "some_hf_model"
    with (
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.litellm") as mock_litellm,
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.tiktoken") as mock_tiktoken,
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.AutoTokenizer") as mock_auto_tokenizer,
    ):
        mock_litellm.get_llm_provider.return_value = [test_model_name]

        mock_tiktoken.encoding_for_model.side_effect = Exception("Tokenizer not found")
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda token: [789] if token == " Yes" else [102]  # noqa: S105
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer
        token_ids = reranker.get_yes_no_token_ids()

        assert token_ids == {789: 1, 102: 1}
        mock_auto_tokenizer.from_pretrained.assert_called_once_with(test_model_name)


def test_get_yes_no_token_ids_no_tokenizer(reranker: LLMReranker, mock_llm: AsyncMock) -> None:
    test_model_name = "some_other_model"
    with (
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.litellm") as mock_litellm,
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.tiktoken") as mock_tiktoken,
        patch("ragbits.document_search.retrieval.rerankers.llm_reranker.AutoTokenizer") as mock_auto_tokenizer,
    ):
        mock_litellm.get_llm_provider.return_value = [test_model_name]
        mock_tiktoken.encoding_for_model.side_effect = Exception("Tokenizer not found")
        mock_auto_tokenizer.from_pretrained.side_effect = Exception("AutoTokenizer not found")
        token_ids = reranker.get_yes_no_token_ids()
        assert token_ids is None
