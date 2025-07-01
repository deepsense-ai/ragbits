from typing import Any

from opentelemetry.metrics import MeterProvider, get_meter

from ragbits.core.audit.metrics.base import MetricHandler, MetricType


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
        super().__init__(metric_prefix=metric_prefix)
        self._meter = get_meter(name=__name__, meter_provider=provider)

    def create_metric(
        self, name: str, unit: str = "", description: str = "", metric_type: MetricType = MetricType.HISTOGRAM
    ) -> Any:  # noqa: ANN401
        """
        Create a metric of the specified type.

        Args:
            name: The metric name.
            unit: The metric unit.
            description: The metric description.
            metric_type: The type of the metric (histogram, counter, gauge).

        Returns:
            The initialized metric.
        """
        if metric_type == MetricType.HISTOGRAM:
            return self._meter.create_histogram(name=name, unit=unit, description=description)
        elif metric_type == MetricType.COUNTER:
            return self._meter.create_counter(name=name, unit=unit, description=description)
        elif metric_type == MetricType.GAUGE:
            return self._meter.create_gauge(name=name, unit=unit, description=description)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

    def _record(self, metric: Any, value: int | float, attributes: dict | None = None) -> None:  # noqa
        """
        Record the value for a specified metric.

        Args:
            metric: The metric to record (histogram, counter, or gauge).
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """
        # Determine metric type by instance
        if hasattr(metric, "record"):
            # Histogram or Gauge (OpenTelemetry Python API)
            metric.record(value, attributes=attributes)
        elif hasattr(metric, "add"):
            # Counter
            metric.add(value, attributes=attributes)
        else:
            raise TypeError("Unsupported metric instance for recording")
