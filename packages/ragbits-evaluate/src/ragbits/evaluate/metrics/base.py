from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from typing_extensions import Self

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate.pipelines.base import EvaluationResult

ResultT = TypeVar("ResultT", bound=EvaluationResult)


class Metric(WithConstructionConfig, Generic[ResultT], ABC):
    """
    Base class for metrics.
    """

    def __init__(self, weight: float = 1.0) -> None:
        """
        Initializes the metric.

        Args:
            weight: Metric value weight in the final score, used during optimization.
        """
        super().__init__()
        self.weight = weight

    @abstractmethod
    def compute(self, results: list[ResultT]) -> dict:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """


class MetricSet(WithConstructionConfig, Generic[ResultT]):
    """
    Represents a set of metrics.
    """

    configuration_key = "metrics"

    def __init__(self, *metrics: Metric[ResultT]) -> None:
        """
        Initializes the metric set.

        Args:
            metrics: The metrics.
        """
        self.metrics = metrics

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `MetricSet` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the metric set.

        Returns:
            An instance of the metric set class initialized with the provided configuration.
        """
        return cls(*[Metric.subclass_from_config(metric_config) for metric_config in config.values()])

    def compute(self, results: list[ResultT]) -> dict:
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
