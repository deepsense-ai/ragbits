from typing import List

import litellm
from pydantic import BaseModel

from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.retrieval.rerankers.base import Reranker


class LiteLLMReranker(BaseModel, Reranker):
    """
    A LiteLLM reranker for providers such as Cohere, Together AI, Azure AI.
    """

    model: str
    top_n: int | None = None
    return_documents: bool = False
    rank_fields: list[str] | None = None
    max_chunks_per_doc: int | None = None

    async def rerank(self, chunks: List[Element], query: str) -> List[Element]:
        """
        Reranking with LiteLLM API.

        Args:
            chunks: The chunks to rerank.
            query: The query to rerank the chunks against.

        Returns:
            The reranked chunks.

        Raises:
            ValueError: If chunks are not a list of TextElement objects.
        """
        if not all(isinstance(chunk, TextElement) for chunk in chunks):
            raise ValueError("All chunks must be TextElement instances")

        documents = [chunk.content if isinstance(chunk, TextElement) else None for chunk in chunks]

        response = await litellm.arerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=self.top_n,
            return_documents=self.return_documents,
            rank_fields=self.rank_fields,
            max_chunks_per_doc=self.max_chunks_per_doc,
        )
        target_order = [result["index"] for result in response.results]
        reranked_chunks = [chunks[i] for i in target_order]

        return reranked_chunks
