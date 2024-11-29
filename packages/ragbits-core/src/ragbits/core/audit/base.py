from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any, Generic, TypeVar

SpanT = TypeVar("SpanT")


class TraceHandler(Generic[SpanT], ABC):
    """
    Base class for all trace handlers.
    """

    def __init__(self) -> None:
        """
        Constructs a new TraceHandler instance.
        """
        super().__init__()
        self._spans = ContextVar[list[SpanT]]("_spans")
        self._spans.set([])

    @abstractmethod
    def start(self, name: str, inputs: dict, current_span: SpanT | None = None) -> SpanT:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The current trace span.

        Returns:
            The updated current trace span.
        """

    @abstractmethod
    def stop(self, outputs: dict, current_span: SpanT) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """

    @abstractmethod
    def error(self, error: Exception, current_span: SpanT) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """

    @contextmanager
    def trace(self, name: str, **inputs: Any) -> Iterator[SimpleNamespace]:  # noqa: ANN401
        """
        Context manager for processing a trace.

        Args:
            name: The name of the trace.
            inputs: The input data.

        Yields:
            The output data.
        """
        self._spans.set(self._spans.get()[:])
        current_span = self._spans.get()[-1] if self._spans.get() else None

        span = self.start(
            name=name,
            inputs=inputs,
            current_span=current_span,
        )
        self._spans.get().append(span)

        try:
            yield (outputs := SimpleNamespace())
        except Exception as exc:
            span = self._spans.get().pop()
            self.error(error=exc, current_span=span)
            raise exc

        span = self._spans.get().pop()
        self.stop(outputs=vars(outputs), current_span=span)
