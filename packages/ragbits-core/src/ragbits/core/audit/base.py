from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import Generic, TypeVar

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
        self._spans = ContextVar[list[SpanT]]("_spans", default=[])

    @abstractmethod
    def start(self, name: str, inputs: dict) -> None:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
        """

    @abstractmethod
    def stop(self, outputs: dict) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
        """

    @abstractmethod
    def error(self, error: Exception) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
        """
