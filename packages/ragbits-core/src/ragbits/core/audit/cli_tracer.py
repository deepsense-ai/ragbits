from rich.console import Console

from ragbits.core.audit import TraceHandler
from ragbits.core.audit.base import SpanT
from ragbits.core.audit.cli_span import CLISpan


class CLITracer(TraceHandler[CLISpan]):
    """
    CLITracer class for all trace handlers.
    """

    def __init__(self) -> None:
        """
        Construct a new CLITracer instance.
        """
        super().__init__()
        self.main_track = []

    def start(self, name: str, inputs: dict, current_span: CLISpan | None = None) -> CLISpan:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The current trace span.

        Returns:
            The updated current trace span.
        """
        parent = self._spans.get()[-1] if self._spans.get() else None
        span = CLISpan(name, parent)

        if parent:
            parent.children.append(span)

        return span

    def stop(self, outputs: dict, current_span: CLISpan) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """

        current_span.end()
        current_span.status = "done"

        if current_span.parent is None:
            console = Console()
            console.print(current_span.to_tree())

    def error(self, error: Exception, current_span: SpanT) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        current_span.end()
        current_span.status = "error"
        if current_span.parent is None:
            console = Console()
            console.print(current_span.to_tree())
