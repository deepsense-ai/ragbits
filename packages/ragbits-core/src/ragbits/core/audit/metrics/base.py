from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TypeVar

MeterT = TypeVar("MeterT")


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


class MetricHandler(ABC):
    """
    Base class for all metric handlers.
    """

    @abstractmethod
    def record(self, metric: HistogramMetric, value: float, attributes: dict | None = None) -> None:
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """
