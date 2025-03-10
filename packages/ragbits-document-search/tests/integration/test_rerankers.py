import pytest

from ragbits.core import audit
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.retrieval.rerankers.base import RerankerOptions
from ragbits.document_search.retrieval.rerankers.litellm import LiteLLMReranker
from ragbits.document_search.retrieval.rerankers.rerankers_answerdotai import AnswerAIReranker

from ..helpers import env_vars_not_set

COHERE_API_KEY_ENV = "COHERE_API_KEY"  # noqa: S105
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"  # noqa: S105


@pytest.mark.skipif(
    env_vars_not_set([COHERE_API_KEY_ENV]),
    reason="Cohere API KEY environment variables not set",
)
async def test_litellm_cohere_reranker_rerank() -> None:
    options = RerankerOptions(top_n=2, max_chunks_per_doc=None)
    reranker = LiteLLMReranker(
        model="cohere/rerank-english-v3.0",
        default_options=options,
    )
    elements = [
        [
            TextElement(
                content="Element 1", document_meta=DocumentMeta.create_text_document_from_literal("Mock document 1")
            ),
            TextElement(
                content="Element 2", document_meta=DocumentMeta.create_text_document_from_literal("Mock document 1")
            ),
            TextElement(
                content="Element 3", document_meta=DocumentMeta.create_text_document_from_literal("Mock document 1")
            ),
        ]
    ]
    query = "Test query"

    results = await reranker.rerank(elements, query)

    assert len(results) == 2


async def test_answerdotai_reranker_rerank() -> None:
    audit.set_trace_handlers("cli")
    options = RerankerOptions(top_n=2)
    reranker = AnswerAIReranker(
        model="mixedbread-ai/mxbai-rerank-large-v1",
        default_options=options,
        model_type="cross-encoder",
    )
    elements = [
        [
            TextElement(
                content="Element 1", document_meta=DocumentMeta.create_text_document_from_literal("Mock document 1")
            ),
            TextElement(
                content="Element 2", document_meta=DocumentMeta.create_text_document_from_literal("Mock document 1")
            ),
            TextElement(
                content="Element 3", document_meta=DocumentMeta.create_text_document_from_literal("Mock document 1")
            ),
        ]
    ]
    query = "Test query"

    results = await reranker.rerank(elements, query)

    assert len(results) == 2
