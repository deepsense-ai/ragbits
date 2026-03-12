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

_HANDLER_REGISTRY: dict[str, tuple[str, str]] = {
    "otel": ("ragbits.core.audit.metrics.otel", "OtelMetricHandler"),
    "logfire": ("ragbits.core.audit.metrics.logfire", "LogfireMetricHandler"),
    "langfuse": ("ragbits.core.audit.metrics.langfuse", "LangfuseMetricHandler"),
}


def _load_handler(name: str) -> MetricHandler:
    """
    Load a metric handler by name.

    Args:
        name: The name of the handler to load.

    Returns:
        An instance of the metric handler.

    Raises:
        ValueError: If the handler is not found.
    """
    import importlib

    name_lower = name.lower()
    if name_lower not in _HANDLER_REGISTRY:
        raise ValueError(f"Handler {name} not found.")

    module_path, class_name = _HANDLER_REGISTRY[name_lower]
    module = importlib.import_module(module_path)
    handler_class = getattr(module, class_name)
    return handler_class()


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
            new_handler = _load_handler(handler)
            if not any(isinstance(item, type(new_handler)) for item in _metric_handlers):
                _metric_handlers.append(new_handler)
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
