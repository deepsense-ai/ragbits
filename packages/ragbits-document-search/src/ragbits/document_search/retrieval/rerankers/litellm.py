from typing import Any, List, overload

from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker

import litellm


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

        Returns:
            The reranked chunks.
        """
        response = litellm.rerank(
            model="cohere/rerank-english-v3.0",
            query=kwargs.get("query"),
            documents=[chunk.content for chunk in chunks],
            top_n=kwargs.get("top_n"),
            return_documents=False
        )
        target_order = [result["index"] for result in response.results]
        reranked_chunks = [chunks[i] for i in target_order]

        return reranked_chunks  
