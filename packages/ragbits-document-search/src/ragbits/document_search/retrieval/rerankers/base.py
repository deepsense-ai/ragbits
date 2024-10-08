import abc

from ragbits.document_search.documents.element import Element


class Reranker(abc.ABC):
    """Reranks chunks retrieved from vector store.
    """

    @staticmethod
    @abc.abstractmethod
    def rerank(chunks: list[Element]) -> list[Element]:
        """Rerank chunks.

        Args:
            chunks: The chunks to rerank.

        Returns:
            The reranked chunks.
        """
