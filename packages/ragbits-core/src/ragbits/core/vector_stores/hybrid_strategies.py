import abc
from operator import add
from uuid import UUID

import numpy as np

from ragbits.core.vector_stores.base import VectorStoreResult


class HybridRetrivalStrategy(abc.ABC):
    """
    A class that can join vectors retrieved from different vector stores into a single list,
    allowing for different strategies for combining results.
    """

    @abc.abstractmethod
    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:
        """
        Joins the multiple lists of results into a single list.

        Args:
            results: The lists of results to join.

        Returns:
            The joined list of results.
        """


class OrderedHybridRetrivalStrategy(HybridRetrivalStrategy):
    """
    A class that orders the results by score and deduplicates them by choosing the first occurrence of each entry.
    This algorithm is also known as "Relative Score Fusion".
    """

    def __init__(self, sum_scores: bool = False) -> None:
        """
        Constructs a new OrderedHybridRetrivalStrategy instance.

        Args:
            sum_scores: if True sums the scores of the same entries, otherwise keeps the best score
                (i.e., the biggest one). Summing scores boosts the results that are present in results
                from multiple vector stores.
        """
        self._sum_scores = sum_scores

    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:
        """
        Joins the multiple lists of results into a single list.

        Args:
            results: The lists of results to join.

        Returns:
            The joined list of results.
        """
        score_operation = add if self._sum_scores else max
        all_results = [result for sublist in results for result in sublist]
        all_results.sort(key=lambda result: result.score, reverse=True)
        end_results: dict[UUID, VectorStoreResult] = {}
        for result in all_results:
            if result.entry.id not in end_results:
                end_results[result.entry.id] = result.model_copy(update={"subresults": [result]})
            else:
                end_results[result.entry.id].score = score_operation(end_results[result.entry.id].score, result.score)
                end_results[result.entry.id].subresults.append(result)

        ordered = list(end_results.values())
        ordered.sort(key=lambda result: result.score, reverse=True)
        return ordered


class ReciprocalRankFusion(HybridRetrivalStrategy):
    """
    An implementation of Reciprocal Rank Fusion (RRF) for combining search results,
    based on the paper "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods":
    https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
    """

    def __init__(self, k_constant: float = 60.0, sum_scores: bool = True) -> None:
        """
        Constructs a new ReciprocalRankFusion instance.

        Args:
            k_constant: The "k" constant used in the RRF formula, meant to mitigate
                the impact of high rankings by outlier systems. The value of 60 is recommended
                by the authors of the RRF paper. Qdrant uses a value of 2.
            sum_scores: if True sums the scores of the same entries, otherwise keeps the best score.
                (i.e., the biggest one). Summing scores boosts the results that are present in results
                from multiple vector stores. Not summing will result in a very simple behavior:
                the list will include first results from all vector stores, then second results
                (excluding the duplicates), and so on. The original version of RRF sums the scores,
                so the default value is True.
        """
        self._k_constant = k_constant
        self._sum_scores = sum_scores

    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:
        """
        Joins the multiple lists of results into a single list using Reciprocal Rank Fusion.

        Args:
            results: The lists of results to join.

        Returns:
            The joined list of results.
        """
        score_operation = add if self._sum_scores else max
        end_results: dict[UUID, VectorStoreResult] = {}
        for result_list in results:
            for i, result in enumerate(result_list):
                score = 1.0 / (i + 1 + self._k_constant)
                if result.entry.id not in end_results:
                    end_results[result.entry.id] = result.model_copy(update={"score": score, "subresults": [result]})
                else:
                    end_results[result.entry.id].score = score_operation(end_results[result.entry.id].score, score)
                    end_results[result.entry.id].subresults.append(result)

        ordered = list(end_results.values())
        ordered.sort(key=lambda result: result.score, reverse=True)
        return ordered


class DistributionBasedScoreFusion(HybridRetrivalStrategy):
    """
    An implementation of Distribution-Based Score Fusion (DBSF) for combining search results,
    based on the "Distribution-Based Score Fusion (DBSF), a new approach to Vector Search Ranking" post:
    https://medium.com/plain-simple-software/distribution-based-score-fusion-dbsf-a-new-approach-to-vector-search-ranking-f87c37488b18
    """

    def __init__(self, sum_scores: bool = False) -> None:
        """
        Constructs a new DistributionBasedScoreFusion instance.

        Args:
            sum_scores: if True sums the scores of the same entries, otherwise keeps the best score.
                (i.e., the biggest one). Summing scores boosts the results that are present in results
                from multiple vector stores. The original DBSF article remains neutral on this matter,
                so the default value is False. Many implementations (like Qdrant) use summing.
        """
        self._sum_scores = sum_scores

    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:  # noqa: PLR6301
        """
        Joins the multiple lists of results into a single list using Distribution-Based Score Fusion.

        Args:
            results: The lists of results to join.

        Returns:
            The joined list of results.
        """
        score_operation = add if self._sum_scores else max
        end_results: dict[UUID, VectorStoreResult] = {}
        scores = np.array([[result.score for result in result_list] for result_list in results])
        mean = np.mean(scores, axis=1)
        std = np.std(scores, axis=1)
        three_std_above = mean + 3 * std
        three_std_below = mean - 3 * std
        normalized_scores = ((scores.T - three_std_below) / (three_std_above - three_std_below)).T

        for i, result_list in enumerate(results):
            for j, result in enumerate(result_list):
                if result.entry.id not in end_results:
                    end_results[result.entry.id] = result.model_copy(
                        update={"score": normalized_scores[i][j], "subresults": [result]}
                    )
                else:
                    end_results[result.entry.id].score = score_operation(
                        end_results[result.entry.id].score, normalized_scores[i][j]
                    )
                    end_results[result.entry.id].subresults.append(result)

        ordered = list(end_results.values())
        ordered.sort(key=lambda result: result.score, reverse=True)

        return ordered
