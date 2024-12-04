import json
from dataclasses import dataclass

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = CliState()
        self.console = Console()

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

    def print_output(self, data: list[dict[str, str]] | list[BaseModel]) -> None:
        """
        Process and display output based on the current state's output type.

        Args:
            data: list of ditionaries or list of pydantic models representing output of CLI function
        """
        if isinstance(data[0], BaseModel):
            data = [output.model_dump(mode="python") for output in data]
        output_type = self.state.output_type
        if output_type == "json":
            try:
                print(json.dumps(data, indent=4))
            except TypeError as err:
                raise ValueError("Output data is not JSON serializable") from err
        else:
            if not data or not isinstance(data, list) or not isinstance(data[0], dict):
                raise ValueError("For text output, data must be a list of dictionaries.")

            table = Table(show_header=True, header_style="bold magenta")
            for key in data[0]:
                table.add_column(key.title())

            for row in data:
                table.add_row(*[str(value) for value in row.values()])

            self.console.print(table)
