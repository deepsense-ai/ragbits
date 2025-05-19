import pytest

from ragbits.core.llms import LiteLLM
from ragbits.core.utils.helpers import env_vars_not_set
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.retrieval.rerankers.answerai import AnswerAIReranker
from ragbits.document_search.retrieval.rerankers.base import RerankerOptions
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker, LiteLLMRerankerOptions
from ragbits.document_search.retrieval.rerankers.llm import LLMReranker, LLMRerankerOptions

COHERE_API_KEY_ENV = "COHERE_API_KEY"  # noqa: S105
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"  # noqa: S105

ELEMENTS = [
    [
        TextElement(content="Element 1", document_meta=DocumentMeta.from_literal("Mock document 1")),
        TextElement(content="Element 2", document_meta=DocumentMeta.from_literal("Mock document 1")),
        TextElement(content="Element 3", document_meta=DocumentMeta.from_literal("Mock document 1")),
    ]
]

QUERY = "Test query"
TOP_N = 2


@pytest.mark.skipif(
    env_vars_not_set([COHERE_API_KEY_ENV]),
    reason="Cohere API KEY environment variables not set",
)
async def test_litellm_cohere_reranker_rerank() -> None:
    options = LiteLLMRerankerOptions(top_n=TOP_N, max_chunks_per_doc=None)
    reranker = LiteLLMReranker(
        model="cohere/rerank-english-v3.0",
        default_options=options,
    )

    results = await reranker.rerank(ELEMENTS, QUERY)
    assert len(results) == TOP_N


async def test_answerdotai_reranker_rerank() -> None:
    options = RerankerOptions(top_n=TOP_N)
    reranker = AnswerAIReranker(
        model="mixedbread-ai/mxbai-rerank-large-v1",
        default_options=options,
        model_type="cross-encoder",
    )

    results = await reranker.rerank(ELEMENTS, QUERY)
    assert len(results) == TOP_N


@pytest.mark.skipif(
    env_vars_not_set([OPENAI_API_KEY_ENV]),
    reason="OPENAI API KEY environment variables not set",
)
async def test_llm_reranker_rerank() -> None:
    options = LLMRerankerOptions(top_n=TOP_N)
    llm = LiteLLM(model_name="gpt-4o")
    reranker = LLMReranker(llm, default_options=options)

    results = await reranker.rerank(elements=ELEMENTS, query=QUERY)
    assert len(results) == TOP_N
