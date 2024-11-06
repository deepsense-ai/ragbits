from collections.abc import Sequence

from ragbits.core.audit import traceable
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class NoopReranker(Reranker):
    """
    A no-op reranker that does not change the order of the elements.
    """

    @classmethod
    def from_config(cls, config: dict) -> "NoopReranker":
        """
        Creates and returns an instance of the NoopReranker class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the NoopReranker instance.

        Returns:
            An initialized instance of the NoopReranker class.
        """
        return cls(default_options=RerankerOptions(**config.get("default_options", {})))

    @traceable
    async def rerank(  # noqa: PLR6301
        self,
        elements: Sequence[Element],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        """
        No reranking, returning the elements in the same order.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            options: The options for reranking.

        Returns:
            The reranked elements.
        """
        return elements
