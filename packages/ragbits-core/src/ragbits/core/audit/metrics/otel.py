from opentelemetry.metrics import MeterProvider, get_meter

from ragbits.core.audit.metrics.base import HISTOGRAM_METRICS, HistogramMetric, MetricHandler


class OtelMetricHandler(MetricHandler):
    """
    OpenTelemetry metric handler.
    """

    def __init__(self, provider: MeterProvider | None = None, metric_prefix: str = "ragbits") -> None:
        """
        Initialize the OtelMetricHandler instance.

        Args:
            provider: The meter provider to use.
            metric_prefix: Prefix for all metric names.
        """
        self._meter = get_meter(name=__name__, meter_provider=provider)
        self._histogram_metrics = {
            key: self._meter.create_histogram(
                name=f"{metric_prefix}_{metric.name}",
                description=metric.description,
                unit=metric.unit,
            )
            for key, metric in HISTOGRAM_METRICS.items()
        }

    def record(self, metric: HistogramMetric, value: float, attributes: dict | None = None) -> None:
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """
        self._histogram_metrics[metric].record(value, attributes=attributes)
