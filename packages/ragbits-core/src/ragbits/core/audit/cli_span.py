import time

from rich.tree import Tree


class CLISpan:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.start_time = time.time()
        self.end_time = None
        self.children = []
        self.status = "started"

    def end(self):
        self.end_time = time.time()

    def to_dict(self):
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "children": [child.to_dict() for child in self.children],
            "parent": self.parent.name if self.parent else None
        }

    def to_tree(self, tree=None, color=None):
        if tree is None:
            tree = Tree(f"[bold blue]{self.name}[/bold blue] (Duration: {self.end_time - self.start_time:.3f}s)")
        else:
            child_tree = tree.add(
                f"[{color}]{self.name}[/{color}] (Duration: {self.end_time - self.start_time:.3f}s)")
            tree = child_tree

        for child in self.children:
            if child.status == "error":
                child.to_tree(tree, "bold red")
            else:
                child.to_tree(tree, "bold green")
        return tree
