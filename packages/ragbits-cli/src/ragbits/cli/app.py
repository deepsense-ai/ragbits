import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table


class OutputType(Enum):
    """Indicates a type of CLI output formatting"""

    text = "text"
    json = "json"


@dataclass()
class CliState:
    """A dataclass describing CLI state"""

    output_type: OutputType = OutputType.text


class CLI(typer.Typer):
    """A CLI class with output formatting"""

    def __init__(self, *args: Any, **kwargs: Any):  # noqa: ANN401
        super().__init__(*args, **kwargs)
        self.state: CliState = CliState()
        self.console: Console = Console()

    def set_output_type(self, output_type: OutputType) -> None:
        """
        Set the output type in the app state
        Args:
            output_type: OutputType
        """
        self.state.output_type = output_type

    def print_output(self, data: list[BaseModel] | BaseModel) -> None:
        """
        Process and display output based on the current state's output type.

        Args:
            data: list of ditionaries or list of pydantic models representing output of CLI function
        """
        if isinstance(data, BaseModel):
            data = [data]
        if len(data) == 0:
            self._print_empty_list()
            return
        first_el_instance = type(data[0])
        if any(not isinstance(datapoint, first_el_instance) for datapoint in data):
            raise ValueError("All the rows need to be of the same type")
        data_dicts: list[dict] = [output.model_dump(mode="python") for output in data]
        output_type = self.state.output_type
        if output_type == OutputType.json:
            print(json.dumps(data_dicts, indent=4))
        elif output_type == OutputType.text:
            table = Table(show_header=True, header_style="bold magenta")
            properties = data[0].model_json_schema()["properties"]
            for key in properties:
                table.add_column(properties[key]["title"])
            for row in data_dicts:
                table.add_row(*[str(value) for value in row.values()])
            self.console.print(table)
        else:
            raise ValueError(f"Output type: {output_type} not supported")

    def _print_empty_list(self) -> None:
        if self.state.output_type == OutputType.text:
            print("Empty data list")
        elif self.state.output_type == OutputType.json:
            print(json.dumps([]))
