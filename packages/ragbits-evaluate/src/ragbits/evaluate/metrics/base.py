from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from omegaconf import DictConfig
from typing_extensions import Self

from ragbits.evaluate.pipelines.base import EvaluationResult

ResultT = TypeVar("ResultT", bound=EvaluationResult)


class Metric(Generic[ResultT], ABC):
    """
    Base class for metrics.
    """

    def __init__(self, config: DictConfig | None = None) -> None:
        """
        Initializes the metric.

        Args:
            config: The metric configuration.
        """
        super().__init__()
        self.config  = config
        # self.config = getattr(config, self.__class__.__name__, DictConfig({}))

    @abstractmethod
    def compute(self, results: list[ResultT]) -> dict[str, Any]:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """



# class MetricSet(Generic[ResultT]):
#     """
#     Represents a set of metrics.
#     """
#
#     def __init__(self, *metrics: type[Metric[ResultT]]) -> None:
#         """
#         Initializes the metric set.
#
#         Args:
#             metrics: The metrics.
#         """
#         self._metrics = metrics
#         self.metrics: list[Metric[ResultT]] = []
#
#     def __call__(self, config: DictConfig | None = None) -> Self:
#         """
#         Initializes the metrics.
#
#         Args:
#             config: The configuration for the metrics.
#
#         Returns:
#             The initialized metric set.
#         """
#         self.metrics = [metric(config) for metric in self._metrics]
#         return self
#
#     def compute(self, results: list[ResultT]) -> dict[str, Any]:
#         """
#         Compute the metrics.
#
#         Args:
#             results: The evaluation results.
#
#         Returns:
#             The computed metrics.
#         """
#         return {name: value for metric in self.metrics for name, value in metric.compute(results).items()}


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
        return {name: value for metric in self.metrics for name, value in metric.compute(results).items()}



