from ragbits.core.audit.metrics.base import MetricHandler, MetricName

__all__ = [
    "MetricHandler",
    "MetricName",
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
                raise ValueError(f"Handler {handler} not found.")
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")


def clear_metric_handlers() -> None:
    """
    Clear all metric handlers.
    """
    global _metric_handlers  # noqa: PLW0602
    _metric_handlers.clear()


def record(metric_name: MetricName, value: float, attributes: dict | None = None) -> None:
    """
    Record a metric using the global metric handlers.

    Args:
        metric_name: The name of the metric.
        value: The value to record.
        attributes: Optional attributes providing context for the metric.
    """
    for handler in _metric_handlers:
        handler.record(metric_name, value, attributes)
