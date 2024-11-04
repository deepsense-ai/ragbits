import asyncio
import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from types import SimpleNamespace
from typing import Any, ParamSpec, TypeVar

from ragbits.core.audit.base import TraceHandler

__all__ = ["TraceHandler", "set_trace_handlers", "trace", "traceable"]

_trace_handlers: list[TraceHandler] = []

Handler = str | TraceHandler

P = ParamSpec("P")
R = TypeVar("R")


def set_trace_handlers(handlers: Handler | list[Handler]) -> None:
    """
    Setup trace handlers.

    Args:
        handlers: List of trace handlers to be used.

    Raises:
        ValueError: If handler is not found.
        TypeError: If handler type is invalid.
    """
    global _trace_handlers  # noqa: PLW0602

    if isinstance(handlers, Handler):
        handlers = [handlers]

    for handler in handlers:  # type: ignore
        if isinstance(handler, TraceHandler):
            _trace_handlers.append(handler)
        elif isinstance(handler, str):
            if handler == "otel":
                from ragbits.core.audit.otel import OtelTraceHandler

                _trace_handlers.append(OtelTraceHandler())
            else:
                raise ValueError(f"Handler {handler} not found.")
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")


@contextmanager
def trace(name: str | None = None, **inputs: Any) -> Iterator[SimpleNamespace]:  # noqa: ANN401
    """
    Context manager for processing a trace.

    Args:
        name: The name of the trace.
        inputs: The input data.

    Yields:
        The output data.
    """
    # We need to go up 2 frames (trace() and __enter__()) to get the parent function.
    parent_frame = inspect.stack()[2].frame
    name = (
        (
            f"{cls.__class__.__qualname__}.{parent_frame.f_code.co_name}"
            if (cls := parent_frame.f_locals.get("self"))
            else parent_frame.f_code.co_name
        )
        if name is None
        else name
    )

    for handler in _trace_handlers:
        handler.start(name=name, inputs=inputs)

    try:
        yield (outputs := SimpleNamespace())
    except Exception as exc:
        for handler in _trace_handlers:
            handler.error(exc)
        raise exc

    for handler in _trace_handlers:
        handler.end(vars(outputs))


def traceable(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator for making a function traceable.

    Args:
        func: The function to be decorated.

    Returns:
        The decorated function.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # TODO: Add support for unnamed arguments.
        with trace(name=func.__qualname__, **kwargs) as outputs:
            returned = func(*args, **kwargs)
            if returned is not None:
                outputs.returned = returned
        return returned

    @wraps(func)
    async def wrapper_async(*args: P.args, **kwargs: P.kwargs) -> R:
        # TODO: Add support for unnamed arguments.
        with trace(name=func.__qualname__, **kwargs) as outputs:
            returned = await func(*args, **kwargs)  # type: ignore
            if returned is not None:
                outputs.returned = returned
        return returned

    return wrapper_async if asyncio.iscoroutinefunction(func) else wrapper  # type: ignore
