import time
from enum import Enum
from typing import Optional

from rich.live import Live
from rich.tree import Tree

from ragbits.core.audit import TraceHandler


class SpanStatus(str, Enum):
    """
    SpanStatus represents the status of the span.
    """

    ERROR = "error"
    STARTED = "started"
    COMPLETED = "completed"


class PrintColor(str, Enum):
    """
    SpanPrintColor represents the color of font for printing the span related information to the console.
    """

    parent_color = "bold blue"
    child_color = "bold green"
    error_color = "bold red"
    faded_color = "grey50"
    key_color = "yellow"


class CLISpan:
    """
    CLI Span represents a single operation within a trace.
    """

    def __init__(self, name: str, inputs: dict | None = None, parent: Optional["CLISpan"] = None):
        """
        Constructs a new CLI Span.
        Sets the start time of the span - the wall time at which the operation started.
        Sets the span status to 'started'.

        Args:
            name: The name of the span.
            inputs: The inputs of the span.
            parent: the parent of initiated span.
        """
        self.name = name
        self.parent = parent
        self.start_time: float = time.time()
        self.end_time: float | None = None
        self.children: list[CLISpan] = []
        self.status: str = SpanStatus.STARTED
        self.inputs: dict = inputs if inputs else {}
        self.outputs: dict = {}

    def end(self) -> None:
        """Sets the current time as the span's end time.
        The span's end time is the wall time at which the operation finished.
        Only the first call to `end` should modify the span,
        further calls are ignored.
        """
        if self.end_time is None:
            self.end_time = time.time()

    def to_tree(self, tree: Tree | None = None, color: str = PrintColor.parent_color) -> Tree:
        """
        Convert theCLISpan object and its children into a Rich Tree structure for console rendering.

        Args:
            tree (Tree, optional): An existing Rich Tree object to which the span will be added.
                               If None, a new tree is created for the root span.
            color (str, optional): The color of the text rendered to console.

        Returns:
            Tree: A Rich Tree object representing the span hierarchy, including its events and children.
        """
        duration = self.end_time - self.start_time if self.end_time else 0.0
        inputs = self._dicts_to_string(self.inputs)
        outputs = self._dicts_to_string(self.outputs)
        if tree is None:
            if self.status == SpanStatus.ERROR:
                color = PrintColor.error_color
            tree = Tree(
                f"[{color}]{self.name}[/{color}] Status: {self.status}; Duration: {duration:.3f}s\n"
                f"[{PrintColor.faded_color}]Inputs: {inputs}\nOutputs: {outputs}[/{PrintColor.faded_color}]"
            )
        else:
            child_tree = tree.add(
                f"[{color}]{self.name}[/{color}] Status: {self.status}; Duration: {duration:.3f}s\n"
                f"[{PrintColor.faded_color}]Inputs: {inputs}\nOutputs: {outputs}[/{PrintColor.faded_color}]"
            )
            tree = child_tree

        for child in self.children:
            if child.status == SpanStatus.ERROR:
                child.to_tree(tree, PrintColor.error_color)
            else:
                child.to_tree(tree, PrintColor.child_color)
        return tree

    def _dicts_to_string(self, input_dict: dict) -> str:
        """
        Converts a dict of dicts to a string representation.

        Args:
            input_dict (dict): A dict.

        Returns:
            str: A string representation.

        """
        parts = []
        max_print_length = 200
        for key, value in input_dict.items():
            if value:
                if isinstance(value, dict):
                    new_string_output = f"\n[{PrintColor.key_color}]{str(key)}:[/{PrintColor.key_color}] "
                    new_string_output += f"{{{self._dicts_to_string(value)}}}"
                else:
                    new_string_output = (
                        f"\n[{PrintColor.key_color}]{str(key)}:[/{PrintColor.key_color}] "
                        f"[{PrintColor.faded_color}]{str(value)}[/{PrintColor.faded_color}]"
                    )
                    if len(new_string_output) > max_print_length:
                        new_string_output = new_string_output[:max_print_length] + f" (...) [/{PrintColor.faded_color}]"
                parts.append(new_string_output)
        return ", ".join(parts)


class CLITraceHandler(TraceHandler[CLISpan]):
    """
    CLITraceHandler class for all trace handlers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.root_span: CLISpan | None = None
        self.live_tree: Tree | None = None
        self.live: Live | None = None

    def start(self, name: str, inputs: dict, current_span: CLISpan | None = None) -> CLISpan:  # noqa: PLR6301
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The current trace span.

        Returns:
            The updated current trace span.
        """
        span = CLISpan(name, inputs, current_span)

        if current_span:
            current_span.children.append(span)
        else:
            self.live_tree = Tree(f"Spans from main {name}")
            self.live = Live(self.live_tree, refresh_per_second=4)
            self.live.start()
            self.root_span = span
        self.update_live()

        return span

    def update_live(self, final: bool = False) -> None:
        """
        Updates the live tree of the current span.

        Args:
            final (bool, optional): Whether the live tree can be stopped or not.
        """
        tree = self.root_span.to_tree() if self.root_span else Tree("No spans yet.")
        if self.live:
            self.live.update(tree)
            if final:
                self.live.stop()

    def stop(self, outputs: dict, current_span: CLISpan) -> None:  # noqa: PLR6301
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        current_span.end()
        current_span.status = SpanStatus.COMPLETED
        current_span.outputs = outputs
        if current_span.parent is None:
            self.update_live(final=True)
        self.update_live()

    def error(self, error: Exception, current_span: CLISpan) -> None:  # noqa: PLR6301
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        current_span.end()
        current_span.status = SpanStatus.ERROR
        current_span.outputs = {"error": str(error)}
        if current_span.parent is None:
            self.update_live(final=True)
        self.update_live()
