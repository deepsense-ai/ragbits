from enum import Enum

from opentelemetry.metrics import Histogram, Meter


class MetricName(Enum):
    """
    Enum representing metrics.
    """

    PROMPT_THROUGHPUT = ("prompt_throughput", "Tracks the response time of LLM calls in seconds", "s")
    TOKEN_THROUGHPUT = ("token_throughput", "Tracks tokens generated per second", "tokens/s")
    INPUT_TOKENS = ("input_tokens", "Tracks the number of input tokens per request", "tokens")
    TIME_TO_FIRST_TOKEN = ("time_to_first_token", "Tracks the time to first token in seconds", "s")

    def __init__(self, value: str, description: str, unit: str):
        self._value_ = value
        self.description = description
        self.unit = unit


class OtelMetricHandler:
    """
    A class to manage and log various metrics for LLM interactions.
    """

    def __init__(self, meter: Meter, metric_prefix: str | None = "ragbits") -> None:
        """
        Args:
            meter: OpenTelemetry Meter instance.
            metric_prefix: Optional prefix to prepend to all metric names.
        """
        self._meter = meter
        self._metric_prefix = metric_prefix
        self.histograms: dict[str, Histogram] = {}

    def setup_histograms(self) -> None:
        """
        Initializes histograms for prompt latency, token throughput, and input tokens.
        """
        self.histograms = {
            metric: self._meter.create_histogram(
                name=f"{self._metric_prefix}_{metric.value}",
                description=metric.description,
                unit=metric.unit,
            )
            for metric in MetricName
        }

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
        self.histograms[metric_name].record(value, attributes=attributes)
