from typing import Any, List, overload

from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker

from litellm import rerank


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
        response = rerank(
            model="cohere/rerank-english-v3.0",
            query=[kwargs.get("query")],
            documents=chunks[0].content,
            top_n=3,
        )

        print(response)

        return chunks  
