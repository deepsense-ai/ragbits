from enum import Enum
from typing import Any

from ragbits.core.audit.metrics.base import MetricHandler, MetricType, register_metric

__all__ = [
    "MetricHandler",
    "MetricType",
    "clear_metric_handlers",
    "record_metric",
    "register_metric",
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
            match handler.lower():
                case "otel":
                    from ragbits.core.audit.metrics.otel import OtelMetricHandler

                    if not any(isinstance(item, OtelMetricHandler) for item in _metric_handlers):
                        _metric_handlers.append(OtelMetricHandler())

                case "logfire":
                    from ragbits.core.audit.metrics.logfire import LogfireMetricHandler

                    if not any(isinstance(item, LogfireMetricHandler) for item in _metric_handlers):
                        _metric_handlers.append(LogfireMetricHandler())

                case _:
                    raise ValueError(f"Not found handler: {handler}")
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")


def clear_metric_handlers() -> None:
    """
    Clear all metric handlers.
    """
    global _metric_handlers  # noqa: PLW0602
    _metric_handlers.clear()


def record_metric(
    metric: str | Enum,
    value: int | float,
    metric_type: MetricType,
    **attributes: Any,  # noqa: ANN401
) -> None:
    """
    Record a metric of any type using the global metric handlers.

    Args:
        metric: The metric key (name or enum value) to record
        value: The value to record
        metric_type: The type of metric (histogram, counter, gauge)
        **attributes: Additional metadata for the metric
    """
    for handler in _metric_handlers:
        handler.record_metric(metric_key=metric, value=value, attributes=attributes, metric_type=metric_type)
