import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Column, Table


class OutputType(Enum):
    """Indicates a type of CLI output formatting"""

    text = "text"
    json = "json"


@dataclass()
class CliState:
    """A dataclass describing CLI state"""

    output_type: OutputType = OutputType.text


cli_state = CliState()

ModelT = TypeVar("ModelT", bound=BaseModel)


def print_output_table(
    data: Sequence[ModelT], columns: Mapping[str, Column] | Sequence[str] | str | None = None
) -> None:
    """
    Display data from Pydantic models in a table format.

    Args:
        data: a list of pydantic models representing output of CLI function
        columns: a list of columns to display in the output table: either as a list, string with comma separated names,
            or for grater control over how the data is displayed a mapping of column names to Column objects.
            If not provided, the columns will be inferred from the model schema.
    """
    console = Console()

    if not data:
        console.print("No results")
        return

    fields = data[0].model_fields

    # Human readable titles for columns
    titles = {key: value.get("title", key) for key, value in data[0].model_json_schema()["properties"].items()}

    # Normalize the list of columns
    if columns is None:
        columns = {key: Column() for key in fields}
    elif isinstance(columns, str):
        columns = {key: Column() for key in columns.split(",")}
    elif isinstance(columns, Sequence):
        columns = {key: Column() for key in columns}

    # Add headers to columns if not provided
    for key in columns:
        if key not in fields:
            Console(stderr=True).print(f"Unknown column: {key}")
            raise typer.Exit(1)

        column = columns[key]
        if column.header == "":
            column.header = titles.get(key, key)

    # Create and print the table
    table = Table(*columns.values(), show_header=True, header_style="bold magenta")
    for row in data:
        table.add_row(*[str(getattr(row, key)) for key in columns])
    console.print(table)


def print_output_json(data: Sequence[ModelT]) -> None:
    """
    Display data from Pydantic models in a JSON format.

    Args:
        data: a list of pydantic models representing output of CLI function
    """
    console = Console()
    console.print(json.dumps([output.model_dump(mode="json") for output in data], indent=4))


def print_output(
    data: Sequence[ModelT] | ModelT, columns: Mapping[str, Column] | Sequence[str] | str | None = None
) -> None:
    """
    Process and display output based on the current state's output type.

    Args:
        data: a list of pydantic models representing output of CLI function
        columns: a list of columns to display in the output table: either as a list, string with comma separated names,
            or for grater control over how the data is displayed a mapping of column names to Column objects.
            If not provided, the columns will be inferred from the model schema.
    """
    if not isinstance(data, Sequence):
        data = [data]

    match cli_state.output_type:
        case OutputType.text:
            print_output_table(data, columns)
        case OutputType.json:
            print_output_json(data)
        case _:
            raise ValueError(f"Unsupported output type: {cli_state.output_type}")
