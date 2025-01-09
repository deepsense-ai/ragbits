from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from omegaconf import OmegaConf

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate.pipelines.base import EvaluationResult

ResultT = TypeVar("ResultT", bound=EvaluationResult)


class Metric(WithConstructionConfig, Generic[ResultT], ABC):
    """
    Base class for metrics.
    """

    def __init__(self, config: dict | None = None) -> None:
        """
        Initializes the metric.

        Args:
            config: The metric configuration.
        """
        super().__init__()
        self.config = OmegaConf.create(config) if config else OmegaConf.create({})
        self.weight: float = getattr(self.config, "weight", 1.0)

    @abstractmethod
    def compute(self, results: list[ResultT]) -> dict[str, Any]:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """


class MetricSet(Generic[ResultT]):
    """
    Represents a set of metrics.
    """

    def __init__(self, *metrics: Metric[ResultT]) -> None:
        """
        Initializes the metric set.

        Args:
            metrics: The metrics.
        """
        self.metrics = metrics

    def compute(self, results: list[ResultT]) -> dict[str, Any]:
        """
        Compute the metrics.

        Args:
            results: The evaluation results.

        Returns:
            The computed metrics.
        """
        return {
            name: metric.weight * value for metric in self.metrics for name, value in metric.compute(results).items()
        }
