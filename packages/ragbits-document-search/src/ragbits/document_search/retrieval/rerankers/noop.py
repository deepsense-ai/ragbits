from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker


class NoopReranker(Reranker):
    """
    A no-op reranker that does not change the order of the chunks.
    """

    async def rerank(self, chunks: list[Element], query: str) -> list[Element]:  # pylint: disable=unused-argument
        """
        No reranking, returning the same chunks as in input.

        Args:
            chunks: The chunks to rerank.
            query: The query to rerank the chunks against.

        Returns:
            The reranked chunks.
        """
        return chunks
