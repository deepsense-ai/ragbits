import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from types import SimpleNamespace
from typing import Any, ParamSpec, TypeVar
from ragbits.core.audit.base import TraceHandler

_trace_handlers: list[TraceHandler] = []

Handler = str | TraceHandler

P = ParamSpec("P")
R = TypeVar("R")


def traceable(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(*args, **kwargs)
        return func(*args, **kwargs)

    @wraps(func)
    async def wrapper_async(*args: P.args, **kwargs: P.kwargs) -> R:
        print("asuync", *args, **kwargs)
        return await func(*args, **kwargs)  # type: ignore

    if asyncio.iscoroutinefunction(func):
        return wrapper_async  # type: ignore
    return wrapper


@asynccontextmanager
async def trace(**inputs: Any) -> AsyncIterator[SimpleNamespace]:
    """
    Context manager for processing an event.

    Args:
        event: The event to be processed.

    Yields:
        The event being processed.
    """
    for handler in _trace_handlers:
        await handler.on_start(**inputs)

    try:
        yield (outputs := SimpleNamespace())
    except Exception as exc:
        for handler in _trace_handlers:
            await handler.on_error(exc)
        raise exc

    for handler in _trace_handlers:
        await handler.on_end(**vars(outputs))


def set_trace_handlers(handlers: Handler | list[Handler]) -> None:
    """
    Setup event handlers.

    Args:
        handlers: List of event handlers to be used.

    Raises:
        ValueError: If handler is not found.
        TypeError: If handler type is invalid.
    """
    global _trace_handlers

    if isinstance(handlers, str):
        handlers = [handlers]

    for handler in handlers:  # type: ignore
        if isinstance(handler, TraceHandler):
            _trace_handlers.append(handler)
        elif isinstance(handler, str):
            if handler == "otel":
                from ragbits.core.audit.otel import OtelTraceHandler
                _trace_handlers.append(OtelTraceHandler())
            if handler == "langsmith":
                from ragbits.core.audit.langsmith import LangSmithTraceHandler
                _trace_handlers.append(LangSmithTraceHandler())
            else:
                raise ValueError(f"Handler {handler} not found.")
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")


__all__ = ["TraceHandler", "traceable", "trace", "set_trace_handlers"]
