from typing import Any, List

import litellm

from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.retrieval.rerankers.base import Reranker


class LiteLLMReranker(Reranker):
    """
    A LiteLLM reranker for providers such as Cohere, Together AI, Azure AI.
    """

    @staticmethod
    def rerank(chunks: List[Element], **kwargs: Any) -> List[Element]:
        """
        Reranking with LiteLLM API.

        Args:
            chunks: The chunks to rerank.
            kwargs: Additional arguments for the LiteLLM API.

        Returns:
            The reranked chunks.
        """
        if not all(isinstance(chunk, TextElement) for chunk in chunks):
            raise ValueError("All chunks must be TextElement instances")

        documents = [chunk.content if isinstance(chunk, TextElement) else None for chunk in chunks]

        response = litellm.rerank(
            model="cohere/rerank-english-v3.0",
            query=kwargs.get("query"),
            documents=documents,
            top_n=kwargs.get("top_n"),
            return_documents=False,
        )
        target_order = [result["index"] for result in response.results]
        reranked_chunks = [chunks[i] for i in target_order]

        return reranked_chunks
