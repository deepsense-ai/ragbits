from opentelemetry.metrics import Histogram, MeterProvider, get_meter

from ragbits.core.audit.metrics.base import MetricHandler


class OtelMetricHandler(MetricHandler[Histogram]):
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
        super().__init__(metric_prefix=metric_prefix)
        self._meter = get_meter(name=__name__, meter_provider=provider)

    def create_histogram(self, name: str, unit: str = "", description: str = "") -> Histogram:
        """
        Create a histogram metric.

        Args:
            name: The histogram metric name.
            unit: The histogram metric unit.
            description: The histogram metric description.

        Returns:
            The initialized histogram metric.
        """
        return self._meter.create_histogram(name=name, unit=unit, description=description)

    def record(self, metric: Histogram, value: int | float, attributes: dict | None = None) -> None:  # noqa: PLR6301
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """
        metric.record(value, attributes=attributes)
