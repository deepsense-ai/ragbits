from abc import ABC, abstractmethod
from enum import Enum
from typing import TypeVar

MeterT = TypeVar("MeterT")


class MetricName(Enum):
    """
    Enum representing metrics.
    """

    PROMPT_THROUGHPUT = ("prompt_throughput", "Tracks the response time of LLM calls in seconds", "s")
    TOKEN_THROUGHPUT = ("token_throughput", "Tracks tokens generated per second", "tokens/s")
    INPUT_TOKENS = ("input_tokens", "Tracks the number of input tokens per request", "tokens")
    TIME_TO_FIRST_TOKEN = ("time_to_first_token", "Tracks the time to first token in seconds", "s")


class MetricHandler(ABC):
    """
    A class to manage and log various metrics for LLM interactions.
    """

    @abstractmethod
    def record(self, metric_name: MetricName, value: float, attributes: dict | None = None) -> None:
        """
        Records the given amount for a specified metric.

        Args:
            metric_name: Enum representing name of the metric to record.
            value: The value to record for the metric.
            attributes: Optional dictionary of attributes providing additional context
            for the metric. Keys are strings, and values can be
            strings, booleans, integers, floats, or sequences of these types.
        """
