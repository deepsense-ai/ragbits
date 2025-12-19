"""Memory-based trace handler for capturing traces in-memory."""

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from ragbits.core.audit.traces.base import TraceHandler


@dataclass
class _TraceSession:
    """A trace session for a single simulation context."""

    root_spans: list["TraceSpan"] = field(default_factory=list)
    current_root: "TraceSpan | None" = None


# Context-local trace session for concurrent isolation
_current_session: ContextVar[_TraceSession | None] = ContextVar("_current_session", default=None)


@dataclass
class TraceSpan:
    """A single trace span capturing an operation."""

    name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float | None = None
    children: list["TraceSpan"] = field(default_factory=list)
    parent: "TraceSpan | None" = None

    @property
    def duration_ms(self) -> float | None:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "name": self.name,
            "inputs": _serialize_value(self.inputs),
            "outputs": _serialize_value(self.outputs),
            "error": self.error,
            "duration_ms": self.duration_ms,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], parent: "TraceSpan | None" = None) -> "TraceSpan":
        """Create from dictionary."""
        span = cls(
            name=data["name"],
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            error=data.get("error"),
            parent=parent,
        )
        # Reconstruct duration from duration_ms
        if data.get("duration_ms") is not None:
            span.start_time = 0
            span.end_time = data["duration_ms"] / 1000
        span.children = [cls.from_dict(child, parent=span) for child in data.get("children", [])]
        return span


def _serialize_value(value: Any) -> Any:  # noqa: ANN401
    """Serialize a value for JSON storage."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_serialize_value(v) for v in value]
    # For other types, convert to string representation
    return repr(value)


class MemoryTraceHandler(TraceHandler[TraceSpan]):
    """Trace handler that stores spans in context-local sessions.

    This handler uses ContextVar to isolate traces per async context,
    allowing concurrent simulations without mixing traces.

    Usage:
        # The handler is registered globally once
        from ragbits.core.audit.traces import set_trace_handlers
        handler = MemoryTraceHandler()
        set_trace_handlers(handler)

    """

    def __init__(self) -> None:
        """Initialize the MemoryTraceHandler."""
        super().__init__()

    @staticmethod
    def _get_session() -> _TraceSession | None:
        """Get the current context's trace session."""
        return _current_session.get()

    def start(self, name: str, inputs: dict, current_span: TraceSpan | None = None) -> TraceSpan:
        """Start a new trace span.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The parent span if any.

        Returns:
            The new trace span.
        """
        span = TraceSpan(
            name=name,
            inputs=_serialize_value(inputs),
            parent=current_span,
        )

        session = self._get_session()
        if session is not None:
            if current_span is not None:
                current_span.children.append(span)
            else:
                session.root_spans.append(span)
                session.current_root = span

        return span

    def stop(self, outputs: dict, current_span: TraceSpan) -> None:
        """Stop a trace span.

        Args:
            outputs: The output data.
            current_span: The span to stop.
        """
        current_span.outputs = _serialize_value(outputs)
        current_span.end_time = time.perf_counter()

        session = self._get_session()
        if session is not None and current_span.parent is None:
            session.current_root = None

    def error(self, error: Exception, current_span: TraceSpan) -> None:
        """Record an error on a span.

        Args:
            error: The error that occurred.
            current_span: The span where the error occurred.
        """
        current_span.error = str(error)
        current_span.end_time = time.perf_counter()

        session = self._get_session()
        if session is not None and current_span.parent is None:
            session.current_root = None

    def get_traces(self) -> list[dict[str, Any]]:
        """Get traces for the current context.

        Returns:
            List of trace span dictionaries.
        """
        session = self._get_session()
        if session is None:
            return []
        return [span.to_dict() for span in session.root_spans]

    @property
    def root_spans(self) -> list[TraceSpan]:
        """Get raw root spans for the current context.

        Returns:
            List of TraceSpan objects (empty list if no session).
        """
        session = self._get_session()
        if session is None:
            return []
        return session.root_spans

    def clear(self) -> None:
        """Clear traces for the current context."""
        session = self._get_session()
        if session is not None:
            session.root_spans.clear()
            session.current_root = None
