import time
from typing import Optional

from rich import print as rich_print
from rich.tree import Tree

from ragbits.core.audit import TraceHandler


class CLISpan:
    """
    CLI Span represents a single operation within a trace.
    """

    def __init__(self, name: str, inputs: dict, parent: Optional["CLISpan"] = None):
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
        self.start_time: float = time.perf_counter()
        self.end_time: float | None = None
        self.children: list[CLISpan] = []
        self.status: str = "started"
        self.inputs: dict = inputs or {}
        self.outputs: dict = {}

    def end(self) -> None:
        """Sets the current time as the span's end time.
        The span's end time is the wall time at which the operation finished.
        Only the first call to `end` should modify the span,
        further calls are ignored.
        """
        if self.end_time is None:
            self.end_time = time.perf_counter()

    def to_tree(self, tree: Tree | None = None, color: str = "bold blue") -> Tree | None:
        """
        Convert theCLISpan object and its children into a Rich Tree structure for console rendering.

        Args:
            tree (Tree, optional): An existing Rich Tree object to which the span will be added.
                               If None, a new tree is created for the root span.
            color (str, optional): The color of the text rendered to console.

        Returns:
            Tree: A Rich Tree object representing the span hierarchy, including its events and children.
        """
        secondary_color = "grey50"
        error_color = "bold red"
        child_color = "bold green"
        duration = self.end_time - self.start_time if self.end_time else 0.0
        inputs = ""
        outputs = ""
        # inputs = dicts_to_string(self.inputs)
        # outputs = dicts_to_string(self.outputs)
        if tree is None:
            tree = Tree(
                f"[{color}]{self.name}[/{color}] Duration: {duration:.3f}s\n"
                f"[{secondary_color}]Inputs: {inputs}\nOutputs: {outputs}[/{secondary_color}]"
            )

        else:
            child_tree = tree.add(
                f"[{color}]{self.name}[/{color}] Duration: {duration:.3f}s\n"
                f"[{secondary_color}]Inputs: {inputs}\nOutputs: {outputs}[/{secondary_color}]"
            )
            tree = child_tree

        for child in self.children:
            if child.status == "error":
                child.to_tree(tree, error_color)
            else:
                child.to_tree(tree, child_color)
        return tree


def dicts_to_string(input_dict: dict) -> str:
    """
    Converts a dict of dicts to a string representation.

    Args:
        input_dict (dict): A dict.

    Returns:
        str: A string representation.

    """
    string_output = ""
    for key, value in input_dict.items():
        if key.startswith("vector"):
            continue
        if value:
            if isinstance(value, dict):
                dicts_to_string(input_dict[key])
            else:
                string_output += "\n[yellow]'" + str(key) + "':[/yellow][grey54]  " + str(value) + "[/grey54]"
    return string_output


class CLITraceHandler(TraceHandler[CLISpan]):
    """
    CLITraceHandler class for all trace handlers.
    """

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

        return span

    def stop(self, outputs: dict, current_span: CLISpan) -> None:  # noqa: PLR6301
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        current_span.end()
        current_span.status = "done"
        current_span.outputs = outputs

        if current_span.parent is None:
            rich_print(current_span.to_tree())

    def error(self, error: Exception, current_span: CLISpan) -> None:  # noqa: PLR6301
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        current_span.end()
        current_span.status = "error"
        if current_span.parent is None:
            rich_print(current_span.to_tree())
