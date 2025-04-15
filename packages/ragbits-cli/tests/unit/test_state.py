from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from pydantic import BaseModel
from pydantic.fields import Field, FieldInfo
from rich.table import Column, Table

from ragbits.cli.state import OutputType, _get_nested_field, print_output, print_output_table
from ragbits.core.sources.local import LocalFileSource


class InnerTestModel(BaseModel):
    id: int
    name: str = Field(title="Name of the inner model", description="Name of the inner model")
    location: LocalFileSource


class OtherTestModel(BaseModel):
    id: int
    name: str
    location: InnerTestModel


class MainTestModel(BaseModel):
    id: int
    name: str
    model: OtherTestModel | None


data = [
    MainTestModel(
        id=1,
        name="A",
        model=OtherTestModel(
            id=11,
            name="aa",
            location=InnerTestModel(id=111, name="aa1", location=LocalFileSource(path=Path("folder_1"))),
        ),
    ),
    MainTestModel(
        id=2,
        name="B",
        model=OtherTestModel(
            id=22,
            name="bb",
            location=InnerTestModel(id=222, name="aa2", location=LocalFileSource(path=Path("folder_2"))),
        ),
    ),
]


@patch("ragbits.cli.state.print_output_table")
@patch("ragbits.cli.state.print_output_json")
def test_print_output_text(mock_print_output_json: MagicMock, mock_print_output_table: MagicMock):
    with patch("ragbits.cli.state.cli_state") as mock_cli_state:
        mock_cli_state.output_type = OutputType.text
        columns = {"id": Column(), "name": Column()}
        print_output(data, columns=columns)
        mock_print_output_table.assert_called_once_with(data, columns)
        mock_print_output_json.assert_not_called()


@patch("ragbits.cli.state.print_output_table")
@patch("ragbits.cli.state.print_output_json")
def test_print_output_json(mock_print_output_json: MagicMock, mock_print_output_table: MagicMock):
    with patch("ragbits.cli.state.cli_state") as mock_cli_state:
        mock_cli_state.output_type = OutputType.json
        print_output(data)
        mock_print_output_table.assert_not_called()
        mock_print_output_json.assert_called_once_with(data)


def test_print_output_unsupported_output_type():
    with patch("ragbits.cli.state.cli_state") as mock_cli_state:
        mock_cli_state.output_type = "unsupported_type"
        with pytest.raises(ValueError, match="Unsupported output type: unsupported_type"):
            print_output(data)


def test_print_output_table():
    with patch("rich.console.Console.print") as mock_print:
        columns = {"id": Column(), "model.location.location.path": Column(), "model.location.name": Column()}
        print_output_table(data, columns)
        mock_print.assert_called_once()
        args, _ = mock_print.call_args_list[0]
        printed_table = args[0]
        assert isinstance(printed_table, Table)
        assert printed_table.columns[0].header == "Id"
        assert printed_table.columns[1].header == "Model Location Location Path"
        assert printed_table.columns[2].header == "Name of the inner model"
        assert printed_table.row_count == 2


def test_get_nested_field():
    column = "model.location.location.path"
    fields = {"name": FieldInfo(annotation=str), "model": FieldInfo(annotation=OtherTestModel)}

    try:
        result = _get_nested_field(column, fields)
        assert result.annotation == Path
    except typer.Exit:
        pytest.fail("typer.Exit was raised unexpectedly")


def test_get_nested_field_wrong_field():
    column_names = [
        ("model.location.wrong_field", "wrong_field"),
        ("model.wrong_path.location.path", "wrong_path"),
        ("wrong_path.location.location.path", "wrong_path"),
        ("model.location.path", "path"),
        ("model.location.location.path.additional_field", "additional_field"),
    ]
    fields = {"name": FieldInfo(annotation=str), "model": FieldInfo(annotation=OtherTestModel)}

    for wrong_column, wrong_fragment in column_names:
        with patch("rich.console.Console.print") as mock_print:
            with pytest.raises(typer.Exit, match="1"):
                _get_nested_field(wrong_column, fields)
            mock_print.assert_called_once_with(f"Unknown column: {wrong_column} ({wrong_fragment} not found)")
