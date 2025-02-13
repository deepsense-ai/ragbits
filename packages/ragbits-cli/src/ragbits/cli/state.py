import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import UnionType
from typing import Optional, TypeVar, Union, get_args, get_origin

import typer
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from rich.console import Console
from rich.table import Column, Table


class OutputType(Enum):
    """Indicates a type of CLI output formatting"""

    text = "text"
    json = "json"


@dataclass()
class CliState:
    """A dataclass describing CLI state"""

    verbose: bool = False
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

    base_fields = {**data[0].model_fields, **data[0].model_computed_fields}

    # Normalize the list of columns
    if columns is None:
        columns = {key: Column() for key in base_fields}
    elif isinstance(columns, str):
        columns = {key: Column() for key in columns.split(",")}
    elif isinstance(columns, Sequence):
        columns = {key: Column() for key in columns}

    # check if columns are correct
    for column_name in columns:
        field = _get_nested_field(column_name, base_fields)
        column = columns[column_name]
        if column.header == "":
            column.header = field.title if field.title else column_name.replace("_", " ").replace(".", " ").title()

    # Create and print the table
    table = Table(*columns.values(), show_header=True, header_style="bold magenta")

    for row in data:
        row_to_add = []
        for key in columns:
            *path_fragments, field_name = key.strip().split(".")
            base_row = row
            for fragment in path_fragments:
                base_row = getattr(base_row, fragment)
            z = getattr(base_row, field_name)
            row_to_add.append(str(z))
        table.add_row(*row_to_add)

    console.print(table)


def _get_nested_field(column_name: str, base_fields: dict) -> FieldInfo:
    """
    Check if column name exists in the model schema.

    Args:
        column_name: name of the column to check
        base_fields: model fields
    Returns:
        field: nested field
    """
    fields = base_fields
    *path_fragments, field_name = column_name.strip().split(".")
    for fragment in path_fragments:
        if fragment not in fields:
            Console(stderr=True).print(
                f"Unknown column: {'.'.join(path_fragments + [field_name])} ({fragment} not found)"
            )
            raise typer.Exit(1)
        model_class = fields[fragment].annotation
        if get_origin(model_class) in [UnionType, Optional, Union]:
            types = get_args(model_class)
            model_class = next((t for t in types if t is not type(None)), None)
        if model_class and issubclass(model_class, BaseModel):
            fields = {**model_class.model_fields, **model_class.model_computed_fields}
    if field_name not in fields:
        Console(stderr=True).print(
            f"Unknown column: {'.'.join(path_fragments + [field_name])} ({field_name} not found)"
        )
        raise typer.Exit(1)
    return fields[field_name]


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
