import asyncio
import inspect
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from functools import wraps
from types import SimpleNamespace
from typing import Any, ParamSpec, TypeVar

from ragbits.core.audit.traces.base import TraceHandler

__all__ = [
    "TraceHandler",
    "clear_trace_handlers",
    "set_trace_handlers",
    "trace",
    "traceable",
]

_trace_handlers: list[TraceHandler] = []

Handler = str | TraceHandler

P = ParamSpec("P")
R = TypeVar("R")


def set_trace_handlers(handlers: Handler | list[Handler]) -> None:
    """
    Set the global trace handlers.

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
                from ragbits.core.audit.traces.otel import OtelTraceHandler

                if not any(isinstance(item, OtelTraceHandler) for item in _trace_handlers):
                    _trace_handlers.append(OtelTraceHandler())
            elif handler == "cli":
                from ragbits.core.audit.traces.cli import CLITraceHandler

                if not any(isinstance(item, CLITraceHandler) for item in _trace_handlers):
                    _trace_handlers.append(CLITraceHandler())
            else:
                raise ValueError(f"Handler {handler} not found.")
        else:
            raise TypeError(f"Invalid handler type: {type(handler)}")


def clear_trace_handlers() -> None:
    """
    Clear all trace handlers.
    """
    global _trace_handlers  # noqa: PLW0602
    _trace_handlers.clear()


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

    with ExitStack() as stack:
        outputs = [stack.enter_context(handler.trace(name, **inputs)) for handler in _trace_handlers]
        yield (out := SimpleNamespace())
        for output in outputs:
            output.__dict__.update(vars(out))


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
        inputs = _get_function_inputs(func, args, kwargs)
        with trace(name=func.__qualname__, **inputs) as outputs:
            returned = func(*args, **kwargs)
            if returned is not None:
                outputs.returned = returned
        return returned

    @wraps(func)
    async def wrapper_async(*args: P.args, **kwargs: P.kwargs) -> R:
        inputs = _get_function_inputs(func, args, kwargs)
        with trace(name=func.__qualname__, **inputs) as outputs:
            returned = await func(*args, **kwargs)  # type: ignore
            if returned is not None:
                outputs.returned = returned
        return returned

    return wrapper_async if asyncio.iscoroutinefunction(func) else wrapper  # type: ignore


def _get_function_inputs(func: Callable, args: tuple, kwargs: dict) -> dict:
    """
    Get the dictionary of inputs for a function based on positional and keyword arguments.

    Args:
        func: The function to get inputs for.
        args: The positional arguments.
        kwargs: The keyword arguments.

    Returns:
        The dictionary of inputs.
    """
    sig_params = inspect.signature(func).parameters
    merged = {}
    pos_args_used = 0

    for param_name, param in sig_params.items():
        if param_name in kwargs:
            merged[param_name] = kwargs[param_name]
        elif pos_args_used < len(args):
            if param_name not in ("self", "cls", "args", "kwargs"):
                merged[param_name] = args[pos_args_used]
            pos_args_used += 1
        elif param.default is not param.empty:
            merged[param_name] = param.default

    merged.update({k: v for k, v in kwargs.items() if k not in merged})

    return merged
