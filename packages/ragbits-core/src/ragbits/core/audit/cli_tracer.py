from rich.console import Console

from ragbits.core.audit import TraceHandler
from ragbits.core.audit.base import SpanT
from ragbits.core.audit.cli_span import CLISpan


class Tracer(TraceHandler[CLISpan]):
    def __init__(self):
        super().__init__()
        self.main_track = []

    def start(self, name: str, inputs: dict, current_span: CLISpan | None = None) -> CLISpan:
        # print("Buu ", self._spans.get())
        parent = self._spans.get()[-1] if self._spans.get() else None
        span = CLISpan(name, parent)

        if parent:
            parent.children.append(span)
            # print("parent span: ", parent.to_dict())
        # Set the current span in the context variable

        # print(f"[Span Started] {name} ")
        return span

    def stop(self, outputs: dict, current_span: CLISpan) -> None:
        current_span.end()
        current_span.status = "done"
        # print(f"[Span Ended] ", current_span.name, current_span.end_time)

        if current_span.parent is None:
            console = Console()
            console.print(current_span.to_tree())

    def error(self, error: Exception, current_span: SpanT) -> None:
        current_span.end()
        current_span.status = "error"
        if current_span.parent is None:
            console = Console()
            console.print(current_span.to_tree())
