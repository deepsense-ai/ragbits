import importlib
from abc import ABC
from typing import Any, Optional

from continuous_eval.metrics.retrieval import PrecisionRecallF1, RankedRetrievalMetrics
from omegaconf import DictConfig

from ragbits.evaluate.metrics.base import Metric, MetricSet
from ragbits.evaluate.pipelines.document_search import DocumentSearchResult


class DocumentSearchMetric(Metric[DocumentSearchResult], ABC):
    """
    Metric for document search evaluation based on Relari backend.
    More details can be found [here](https://docs.relari.ai/category/retrieval-rag).
    """

    metric_cls: type[PrecisionRecallF1 | RankedRetrievalMetrics]

    def __init__(self, config: Optional[DictConfig] = None) -> None:
        """
        Initializes the metric.

        Args:
            config: The metric configuration.
        """
        super().__init__(config)

        matching_strategy = getattr(
            importlib.import_module("continuous_eval.metrics.retrieval.matching_strategy"),
            self.config.matching_strategy,
        )
        self.metric = self.metric_cls(matching_strategy(**self.config.options))

    def compute(self, results: list[DocumentSearchResult]) -> dict[str, Any]:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        return self.metric.aggregate(
            [self.metric(result.predicted_passages, result.reference_passages) for result in results]
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


document_search_metrics = MetricSet(DocumentSearchPrecisionRecallF1, DocumentSearchRankedRetrievalMetrics)
