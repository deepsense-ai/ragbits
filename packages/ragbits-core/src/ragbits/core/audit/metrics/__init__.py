from typing import Any

from ragbits.core.audit.metrics.base import HistogramMetric, MetricHandler

__all__ = [
    "HistogramMetric",
    "MetricHandler",
    "clear_metric_handlers",
    "record",
    "set_metric_handlers",
]

Handler = str | MetricHandler

_metric_handlers: list[MetricHandler] = []


def set_metric_handlers(handlers: Handler | list[Handler]) -> None:
    """
    Set the global metric handlers.

    Args:
        handlers: List of metric handlers to be used.

    Raises:
        ValueError: If handler is not found.
        TypeError: If handler type is invalid.
    """
    global _metric_handlers  # noqa: PLW0602

    if isinstance(handlers, Handler):
        handlers = [handlers]

    for handler in handlers:
        if isinstance(handler, MetricHandler):
            _metric_handlers.append(handler)
        elif isinstance(handler, str):
            if handler == "otel":
                from ragbits.core.audit.metrics.otel import OtelMetricHandler

                if not any(isinstance(item, OtelMetricHandler) for item in _metric_handlers):
                    _metric_handlers.append(OtelMetricHandler())
            else:
                raise ValueError(f"Not found handler: {handler}")
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")


def clear_metric_handlers() -> None:
    """
    Clear all metric handlers.
    """
    global _metric_handlers  # noqa: PLW0602
    _metric_handlers.clear()


def create_histogram(name: str, unit: str = "", description: str = "") -> str:
    """
    Create a histogram metric.

    Args:
        name: The histogram metric name.
        unit: The histogram metric unit.
        description: The histogram metric description.

    Returns:
        The initialized histogram metric.
    """
    for handler in _metric_handlers:
        handler.register_histogram(name=name, unit=unit, description=description)
    return name


def record(metric: HistogramMetric | str, value: int | float, **attributes: Any) -> None:  # noqa: ANN401
    """
    Record a histogram metric using the global metric handlers.

    Args:
        metric: The histogram metric name to record.
        value: The value to record.
        attributes: Additional metadata for the metric.
    """
    for handler in _metric_handlers:
        handler.record_histogram(metric=metric, value=value, attributes=attributes)
