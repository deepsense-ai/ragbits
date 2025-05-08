from opentelemetry.metrics import Meter, get_meter

from ragbits.core.audit.metrics.base import MetricHandler, MetricName


class OtelMetricHandler(MetricHandler):
    """
    A class to manage and log various metrics for LLM interactions.
    """

    def __init__(self, meter: Meter | None = None, metric_prefix: str | None = "ragbits") -> None:
        """
        Args:
            meter: OpenTelemetry Meter instance.
            metric_prefix: Optional prefix to prepend to all metric names.
        """
        self._meter = meter or get_meter("ragbits")
        self._metric_prefix = metric_prefix
        self.histograms = {
            metric: self._meter.create_histogram(
                name=f"{self._metric_prefix}_{metric.value[0]}",
                description=metric.value[1],
                unit=metric.value[2],
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
        print(metric_name, value)
        self.histograms[metric_name].record(value, attributes=attributes)
