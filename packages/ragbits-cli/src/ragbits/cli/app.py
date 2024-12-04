import json
from dataclasses import dataclass
from typing import Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table


@dataclass()
class CliState:
    """A dataclass describing CLI state"""

    output_type: str = "text"


class CLI(typer.Typer):
    """A CLI class with output formatting"""

    def __init__(self, *args: Any, **kwargs: Any):  # noqa: ANN401
        super().__init__(*args, **kwargs)
        self.state: CliState = CliState()
        self.console: Console = Console()

    def set_output_type(self, output_type: str) -> None:
        """
        Set the output type in the app state
        Args:
            output_type: str
        Raises:
            ValueError - if the output_type is not `json` or `text`
        """
        if output_type not in ["text", "json"]:
            raise ValueError("Output type must be either 'text' or 'json'")
        self.state.output_type = output_type

    def print_output(self, data: list[BaseModel]) -> None:
        """
        Process and display output based on the current state's output type.

        Args:
            data: list of ditionaries or list of pydantic models representing output of CLI function
        """
        first_el_instance = type(data[0])
        if any(not isinstance(datapoint, first_el_instance) for datapoint in data):
            raise ValueError("All the rows need to be of the same type")
        data_dicts: list[dict] = [output.model_dump(mode="python") for output in data]
        output_type = self.state.output_type
        if output_type == "json":
            print(json.dumps(data_dicts, indent=4))
        elif output_type == "text":
            table = Table(show_header=True, header_style="bold magenta")
            for key in data_dicts[0]:
                table.add_column(key.title())
            for row in data_dicts:
                table.add_row(*[str(value) for value in row.values()])
            self.console.print(table)
