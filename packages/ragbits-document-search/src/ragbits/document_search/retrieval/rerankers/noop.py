
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker


class NoopReranker(Reranker):
    """
    A no-op reranker that does not change the order of the chunks.
    """

    @staticmethod
    def rerank(chunks: list[Element]) -> list[Element]:
        """
        No reranking, returning the same chunks as in input.

        Args:
            chunks: The chunks to rerank.

        Returns:
            The reranked chunks.
        """
        return chunks
