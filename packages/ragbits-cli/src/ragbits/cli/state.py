import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

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


cli_state = CliState()


def print_output(data: Sequence[BaseModel] | BaseModel) -> None:
    """
    Process and display output based on the current state's output type.

    Args:
        data: a list of pydantic models representing output of CLI function
    """
    console = Console()
    if isinstance(data, BaseModel):
        data = [data]
    if len(data) == 0:
        _print_empty_list()
        return
    first_el_instance = type(data[0])
    if any(not isinstance(datapoint, first_el_instance) for datapoint in data):
        raise ValueError("All the rows need to be of the same type")
    data_dicts: list[dict] = [output.model_dump(mode="python") for output in data]
    output_type = cli_state.output_type
    if output_type == OutputType.json:
        console.print(json.dumps(data_dicts, indent=4))
    elif output_type == OutputType.text:
        table = Table(show_header=True, header_style="bold magenta")
        properties = data[0].model_json_schema()["properties"]
        for key in properties:
            table.add_column(properties[key]["title"])
        for row in data_dicts:
            table.add_row(*[str(value) for value in row.values()])
        console.print(table)
    else:
        raise ValueError(f"Output type: {output_type} not supported")


def _print_empty_list() -> None:
    if cli_state.output_type == OutputType.text:
        print("Empty data list")
    elif cli_state.output_type == OutputType.json:
        print(json.dumps([]))
