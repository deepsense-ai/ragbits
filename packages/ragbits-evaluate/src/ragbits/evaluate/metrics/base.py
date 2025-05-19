import asyncio
from abc import ABC, abstractmethod
from types import ModuleType
from typing import ClassVar, Generic

from typing_extensions import Self

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate import metrics
from ragbits.evaluate.pipelines.base import EvaluationResultT


class Metric(WithConstructionConfig, Generic[EvaluationResultT], ABC):
    """
    Base class for metrics.
    """

    default_module: ClassVar[ModuleType | None] = metrics
    configuration_key: ClassVar[str] = "metric"

    def __init__(self, weight: float = 1.0) -> None:
        """
        Initialize the metric.

        Args:
            weight: Metric value weight in the final score, used during optimization.
        """
        super().__init__()
        self.weight = weight

    @abstractmethod
    async def compute(self, results: list[EvaluationResultT]) -> dict:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """


class MetricSet(WithConstructionConfig, Generic[EvaluationResultT]):
    """
    Represents a set of metrics.
    """

    configuration_key: ClassVar[str] = "metrics"
    default_module: ClassVar[ModuleType | None] = metrics

    def __init__(self, *metrics: Metric[EvaluationResultT]) -> None:
        """
        Initialize the metric set.

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

    async def compute(self, results: list[EvaluationResultT]) -> dict:
        """
        Compute the metrics.

        Args:
            results: The evaluation results.

        Returns:
            The computed metrics.
        """
        metric_results = await asyncio.gather(*[metric.compute(results) for metric in self.metrics])
        return {
            name: metric.weight * value
            for metric, result in zip(self.metrics, metric_results, strict=False)
            for name, value in result.items()
        }
