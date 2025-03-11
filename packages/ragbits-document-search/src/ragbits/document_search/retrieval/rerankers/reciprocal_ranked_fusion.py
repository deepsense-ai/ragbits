from collections import defaultdict
from collections.abc import Sequence

from ragbits.core.audit import traceable
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class ReciprocalRankFusionReranker(Reranker[RerankerOptions]):
    """
    A reranker that implements the Reciprocal Rank Fusion (RRF) algorithm to
    combine multiple ranked result sets into a single reranked list.

    RRF is a method that assigns scores to documents based on their positions
    in multiple ranked lists, allowing for fusion of diverse ranking sources
    without the need for tuning.

    The score for each document is calculated using the formula:

        score = sum(1.0 / (k + rank(q, d)))

    where:
        - k is a ranking constant (1 is used here)
        - q is a query in the set of queries
        - d is a document in the result set
        - rank(q, d) is the position of d in the ranking list for q (starting from 1)
    """

    options_cls = RerankerOptions

    @traceable
    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        """
        Reranks elements using the Reciprocal Rank Fusion (RRF) algorithm.

        Args:
            elements: A list of ranked lists of elements to be fused.
            query: The query string for reranking.
            options: Options for reranking.

        Returns:
            The reranked elements.
        """
        if len(elements) == 1:
            return elements[0]

        merged_options = (self.default_options | options) if options else self.default_options

        scores: dict[str, float] = defaultdict(float)
        elements_map: dict[str, Element] = {}

        for query_elements in elements:
            for rank, document in enumerate(query_elements):
                if not document.key:
                    continue
                scores[document.key] += 1 / (rank + 1 + 1)
                elements_map[document.key] = document

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [elements_map[item[0]] for item in sorted_scores][: merged_options.top_n]
