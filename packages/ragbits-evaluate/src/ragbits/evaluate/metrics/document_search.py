import importlib
from abc import ABC

from continuous_eval.metrics.retrieval import PrecisionRecallF1, RankedRetrievalMetrics
from continuous_eval.metrics.retrieval.matching_strategy import MatchingStrategy
from typing_extensions import Self

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.document_search import DocumentSearchResult


class DocumentSearchMetric(Metric[DocumentSearchResult], ABC):
    """
    Metric for document search evaluation based on Relari backend.
    More details can be found [here](https://docs.relari.ai/category/retrieval-rag).
    """

    metric_cls: type[PrecisionRecallF1 | RankedRetrievalMetrics]

    def __init__(self, matching_strategy: MatchingStrategy, weight: float = 1.0) -> None:
        """
        Initialize the document search metric.

        Args:
            matching_strategy: Matching strategys that determine relevance.
            weight: Metric value weight in the final score, used during optimization.
        """
        super().__init__(weight=weight)
        self.metric = self.metric_cls(matching_strategy)

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `DocumentSearchMetric` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the metric.

        Returns:
            An instance of the metric class initialized with the provided configuration.
        """
        matching_strategy_cls = getattr(
            importlib.import_module("continuous_eval.metrics.retrieval.matching_strategy"),
            config["matching_strategy"]["type"],
        )
        matching_strategy = matching_strategy_cls(**config["matching_strategy"]["config"])
        return cls(matching_strategy=matching_strategy, weight=config.get("weight", 1.0))

    async def compute(self, results: list[DocumentSearchResult]) -> dict:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        return self.metric.aggregate(
            [
                self.metric(
                    [
                        element.text_representation
                        for element in result.predicted_elements
                        if element.text_representation
                    ],
                    result.reference_passages,
                )
                for result in results
                if result.reference_passages is not None
            ]
        )


class DocumentSearchPrecisionRecallF1(DocumentSearchMetric):
    """
    Precision, recall, and F1 score for context retrieval.
    More details can be found [here](https://docs.relari.ai/metrics/Retrieval/Deterministic/precision_recall).
    """

    metric_cls = PrecisionRecallF1


class DocumentSearchRankedRetrievalMetrics(DocumentSearchMetric):
    """
    Rank-aware metrics takes into account the order in which the contexts are retrieved.
    More details can be found [here](https://docs.relari.ai/metrics/Retrieval/Deterministic/rank_aware_metrics).
    """

    metric_cls = RankedRetrievalMetrics
