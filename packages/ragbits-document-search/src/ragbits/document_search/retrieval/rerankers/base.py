import abc
from typing import Any

from pydantic import BaseModel

from ragbits.document_search.documents.element import Element


class Reranker(BaseModel, abc.ABC):
    """
    Reranks chunks retrieved from vector store.
    """

    @abc.abstractmethod
    def rerank(self, chunks: list[Element], query: str) -> list[Element]:
        """
        Rerank chunks.

        Args:
            chunks: The chunks to rerank.
            query: The query to rerank the chunks against.

        Returns:
            The reranked chunks.
        """
