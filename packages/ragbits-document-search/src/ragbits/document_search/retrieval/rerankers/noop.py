from collections.abc import Sequence

from ragbits.core.audit import traceable
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class NoopReranker(Reranker[RerankerOptions]):
    """
    A no-op reranker that does not change the order of the elements.
    """

    options_cls = RerankerOptions

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
