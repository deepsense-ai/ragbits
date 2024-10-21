import importlib
from typing import Any, Optional

from continuous_eval.metrics.retrieval import PrecisionRecallF1, RankedRetrievalMetrics
from omegaconf import DictConfig

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.document_search import DocumentSearchResult


class DocumentSearchMetric(Metric[DocumentSearchResult]):
    """
    Base class for metrics used in document search evaluation.
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
    Precision measures the accuracy of the retrieved documents. It is the ratio of the number of relevant documents
    """

    metric_cls = PrecisionRecallF1


class DocumentSearchRankedRetrievalMetrics(DocumentSearchMetric):
    """
    Precision measures the accuracy of the retrieved documents. It is the ratio of the number of relevant documents
    """

    metric_cls = RankedRetrievalMetrics
