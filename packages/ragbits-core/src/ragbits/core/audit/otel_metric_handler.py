from opentelemetry.metrics import Histogram, Meter


class OtelMetricHandler:
    """
    A class to manage and log various metrics for LLM interactions.
    """

    def __init__(self, meter: Meter) -> None:
        self._meter = meter
        self.histograms: dict[str, Histogram] = {}

    def setup_histograms(self) -> None:
        """
        Initializes histograms for prompt latency, token throughput, and input tokens.
        """
        self.histograms = {
            "prompt_throughput": self._meter.create_histogram(
                name="prompt_throughput", description="Tracks the response time of LLM calls", unit="ms"
            ),
            "token_throughput": self._meter.create_histogram(
                name="token_throughput", description="Tracks tokens generated per second", unit="tokens/s"
            ),
            "input_tokens": self._meter.create_histogram(
                name="input_tokens", description="Tracks the number of input tokens per request", unit="tokens"
            ),
            "time_to_first_token": self._meter.create_histogram(
                name="time_to_first_token", description="Tracks the time to first token in milliseconds", unit="ms"
            ),
        }

    def record(self, metric_name: str, value: float) -> None:
        """
        Records the given amount for a specified metric.

        Args:
            metric_name: Name of the metric to record (e.g., "prompt_throughput").
            value: The value to record for the metric.
        """
        self.histograms[metric_name].record(value)
