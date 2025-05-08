from opentelemetry.metrics import Meter

from ragbits.core.audit.metrics.otel import MetricName, OtelMetricHandler

__all__ = [
    "MetricName",
    "OtelMetricHandler",
    "record_metric",
    "set_metric_handler",
]

_metric_handler: OtelMetricHandler | None = None


def set_metric_handler(meter: Meter) -> None:
    """
    Sets up the global metric handler.

    Args:
        meter: OpenTelemetry Meter instance to be used for metrics.
    """
    global _metric_handler  # noqa: PLW0603
    _metric_handler = OtelMetricHandler(meter)
    _metric_handler.setup_histograms()


def record_metric(metric_name: MetricName, value: float, attributes: dict | None = None) -> None:
    """
    Records a metric using the global metric handler.

    Args:
        metric_name: The name of the metric.
        value: The value to record.
        attributes: Optional attributes providing context for the metric.
    """
    if _metric_handler:
        _metric_handler.record(metric_name, value, attributes)
