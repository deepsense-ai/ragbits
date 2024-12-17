import time
from typing import Optional
from rich.tree import Tree


class CLISpan:
    """
    CLI Span represents a single operation within a trace.
    """

    def __init__(self, name: str, parent: Optional['CLISpan'] = None):
        """
        Constructs a new CLI Span.
        Sets the start time of the span - the wall time at which the operation started.
        Sets the span status to 'started'.
        Args:
            name: The name of the span.
            parent: the parent of initiated span.
        """
        self.name = name
        self.parent = parent
        self.start_time = time.time()
        self.end_time = None
        self.children = []
        self.status = "started"

    def end(self) -> None:
        """Sets the current time as the span's end time.
        The span's end time is the wall time at which the operation finished.
        Only the first call to `end` should modify the span,
        further calls are ignored.
        """
        if self.end_time is None:
            self.end_time = time.time()

    def to_dict(self) -> dict:
        """
        Convert the CLISpan object and its children into a dictionary representation.
        Returns:
        dict: A dictionary containing the span's name, start time, end time, events,
              and a list of its children's dictionary representations.
        """
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "children": [child.to_dict() for child in self.children],
            "parent": self.parent.name if self.parent else None,
        }

    def to_tree(self, tree: Tree = None, color: str = None) -> Tree:
        """
        Convert theCLISpan object and its children into a Rich Tree structure for console rendering.
        Args:
            tree (Tree, optional): An existing Rich Tree object to which the span will be added.
                               If None, a new tree is created for the root span.
            color (str, optional): The color of the text rendered to console.
        Returns:
            Tree: A Rich Tree object representing the span hierarchy, including its events and children.
        """
        if tree is None:
            tree = Tree(f"[bold blue]{self.name}[/bold blue] (Duration: {self.end_time - self.start_time:.3f}s)")
        else:
            child_tree = tree.add(f"[{color}]{self.name}[/{color}] (Duration: {self.end_time - self.start_time:.3f}s)")
            tree = child_tree

        for child in self.children:
            if child.status == "error":
                child.to_tree(tree, "bold red")
            else:
                child.to_tree(tree, "bold green")
        return tree
