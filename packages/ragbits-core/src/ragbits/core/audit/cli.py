import time
from enum import Enum

from rich.live import Live
from rich.tree import Tree

from ragbits.core.audit import TraceHandler


class SpanStatus(Enum):
    """
    SpanStatus represents the status of the span.
    """

    ERROR = "ERROR"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"


class PrintColor(str, Enum):
    """
    SpanPrintColor represents the color of font for printing the span related information to the console.
    """

    BLUE = "bold blue"
    GREEN = "bold green"
    RED = "bold red"
    GRAY = "grey50"
    PURPLE = "plum4"


class CLISpan:
    """
    CLI Span represents a single operation within a trace.
    """

    def __init__(self, name: str, attributes: dict, parent: "CLISpan | None" = None) -> None:
        """
        Constructs a new CLI Span.

        Args:
            name: The name of the span.
            attributes: The attributes of the span.
            parent: the parent of initiated span.
        """
        self.name = name
        self.parent = parent
        self.attributes = attributes
        self.start_time = time.perf_counter()
        self.end_time: float | None = None
        self.status = SpanStatus.STARTED
        self.tree = Tree("")
        if self.parent:
            self.parent.tree.add(self.tree)

    def update(self) -> None:
        """
        Updates tree label based on span state.
        """
        elapsed = f": {(self.end_time - self.start_time):.3f}s" if self.end_time else " ..."
        color = {
            SpanStatus.ERROR: PrintColor.RED,
            SpanStatus.STARTED: PrintColor.BLUE,
            SpanStatus.COMPLETED: PrintColor.GREEN,
        }[self.status]
        name = f"[{color}]{self.name}[/{color}][{PrintColor.GRAY}]{elapsed}[/{PrintColor.GRAY}]"

        # TODO: Remove truncating after implementing better CLI formatting.
        attrs = [
            f"[{PrintColor.PURPLE}]{k}:[/{PrintColor.PURPLE}] "
            f"[{PrintColor.GRAY}]{v[:120] + ' (...)' if len(v) > 120 else v}[/{PrintColor.GRAY}]"  # noqa: PLR2004
            for k, v in self.attributes.items()
        ]
        self.tree.label = f"{name}\n{chr(10).join(attrs)}" if attrs else name

    def end(self) -> None:
        """
        Sets the current time as the span's end time.
        The span's end time is the wall time at which the operation finished.
        Only the first call to `end` should modify the span, further calls are ignored.
        """
        if self.end_time is None:
            self.end_time = time.perf_counter()


class CLITraceHandler(TraceHandler[CLISpan]):
    """
    CLITraceHandler class for all trace handlers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.live = Live(auto_refresh=False)

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
        attributes = _format_attributes(inputs, prefix="inputs")
        span = CLISpan(
            name=name,
            attributes=attributes,
            parent=current_span,
        )
        if current_span is None:
            self.live = Live(auto_refresh=False)
            self.live.start()
            self.tree = span.tree

        span.update()
        self.live.update(self.tree, refresh=True)

        return span

    def stop(self, outputs: dict, current_span: CLISpan) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        attributes = _format_attributes(outputs, prefix="outputs")
        current_span.attributes.update(attributes)
        current_span.status = SpanStatus.COMPLETED
        current_span.end()

        current_span.update()
        self.live.update(self.tree, refresh=True)

        if current_span.parent is None:
            self.live.stop()

    def error(self, error: Exception, current_span: CLISpan) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        attributes = _format_attributes({"message": str(error), **vars(error)}, prefix="error")
        current_span.attributes.update(attributes)
        current_span.status = SpanStatus.ERROR
        current_span.end()

        current_span.update()
        self.live.update(self.tree, refresh=True)

        if current_span.parent is None:
            self.live.stop()


def _format_attributes(data: dict, prefix: str | None = None) -> dict:
    """
    Format attributes for CLI.

    Args:
        data: The data to format.
        prefix: The prefix to use for the keys.

    Returns:
        The formatted attributes.
    """
    flattened = {}

    for key, value in data.items():
        current_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            flattened.update(_format_attributes(value, current_key))
        elif isinstance(value, list | tuple):
            flattened[current_key] = repr(
                [
                    item if isinstance(item, str | float | int | bool) else repr(item)
                    for item in value  # type: ignore
                ]
            )
        elif isinstance(value, str | float | int | bool):
            flattened[current_key] = str(value)
        else:
            flattened[current_key] = repr(value)

    return flattened
