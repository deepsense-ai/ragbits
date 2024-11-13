import importlib
from abc import ABC
from typing import Any

from continuous_eval.metrics.retrieval import PrecisionRecallF1, RankedRetrievalMetrics
from continuous_eval.metrics.retrieval.matching_strategy import RougeChunkMatch
from omegaconf import DictConfig, OmegaConf

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.document_search import DocumentSearchResult


class DocumentSearchMetric(Metric[DocumentSearchResult], ABC):
    """
    Metric for document search evaluation based on Relari backend.
    More details can be found [here](https://docs.relari.ai/category/retrieval-rag).
    """

    metric_cls: type[PrecisionRecallF1 | RankedRetrievalMetrics]
    default_matching_strategy: type[RougeChunkMatch] = RougeChunkMatch
    default_matching_options: DictConfig = OmegaConf.create({"threshold": 0.5})

    def __init__(self, config: DictConfig | None = None) -> None:
        """
        Initializes the metric.

        Args:
            config: The metric configuration.
        """
        super().__init__(config)
        if not self.config:
            matching_strategy = self.default_matching_strategy
            options = self.default_matching_options

        else:
            matching_strategy = getattr(
                importlib.import_module("continuous_eval.metrics.retrieval.matching_strategy"),
                self.config.matching_strategy,
            )
            options = self.config.options
        self.metric = self.metric_cls(matching_strategy(**options))

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
