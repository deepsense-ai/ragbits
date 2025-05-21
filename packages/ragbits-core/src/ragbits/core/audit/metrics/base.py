from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Generic, TypeVar

HistogramT = TypeVar("HistogramT")


@dataclass
class Metric:
    """
    Represents the metric configuration data.
    """

    name: str
    description: str
    unit: str


class HistogramMetric(Enum):
    """
    Histogram metric types that can be recorded.
    """

    PROMPT_THROUGHPUT = auto()
    TOKEN_THROUGHPUT = auto()
    INPUT_TOKENS = auto()
    TIME_TO_FIRST_TOKEN = auto()


HISTOGRAM_METRICS = {
    HistogramMetric.PROMPT_THROUGHPUT: Metric(
        name="prompt_throughput",
        description="Tracks the response time of LLM calls in seconds",
        unit="s",
    ),
    HistogramMetric.TOKEN_THROUGHPUT: Metric(
        name="token_throughput",
        description="Tracks tokens generated per second",
        unit="tokens/s",
    ),
    HistogramMetric.INPUT_TOKENS: Metric(
        name="input_tokens",
        description="Tracks the number of input tokens per request",
        unit="tokens",
    ),
    HistogramMetric.TIME_TO_FIRST_TOKEN: Metric(
        name="time_to_first_token",
        description="Tracks the time to first token in seconds",
        unit="s",
    ),
}


class MetricHandler(Generic[HistogramT], ABC):
    """
    Base class for all metric handlers.
    """

    def __init__(self, metric_prefix: str = "ragbits") -> None:
        """
        Initialize the MetricHandler instance.

        Args:
            metric_prefix: Prefix for all metric names.
        """
        super().__init__()
        self._metric_prefix = metric_prefix
        self._histogram_metrics: dict[str, HistogramT] = {}

    @abstractmethod
    def create_histogram(self, name: str, unit: str = "", description: str = "") -> HistogramT:
        """
        Create a histogram metric.

        Args:
            name: The histogram metric name.
            unit: The histogram metric unit.
            description: The histogram metric description.

        Returns:
            The initialized histogram metric.
        """

    @abstractmethod
    def record(self, metric: HistogramT, value: int | float, attributes: dict | None = None) -> None:
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """

    def register_histogram(self, name: str, unit: str = "", description: str = "") -> None:
        """
        Register a histogram metric.

        Args:
            name: The histogram metric name.
            unit: The histogram metric unit.
            description: The histogram metric description.

        Returns:
            The registered histogram metric.
        """
        self._histogram_metrics[name] = self.create_histogram(
            name=f"{self._metric_prefix}_{name}",
            unit=unit,
            description=description,
        )

    def record_histogram(
        self, metric: HistogramMetric | str, value: int | float, attributes: dict | None = None
    ) -> None:
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric name to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """
        if histogram_metric := HISTOGRAM_METRICS.get(metric):  # type: ignore
            metric_name = histogram_metric.name
            if metric_name not in self._histogram_metrics:
                self.register_histogram(
                    name=metric_name,
                    unit=histogram_metric.unit,
                    description=histogram_metric.description,
                )
        else:
            metric_name = str(metric)
            if metric_name not in self._histogram_metrics:
                self.register_histogram(metric_name)

        self.record(
            metric=self._histogram_metrics[metric_name],
            value=value,
            attributes=attributes,
        )
