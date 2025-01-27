from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from rich.table import Column, Table

from ragbits.cli.state import OutputType, check_column_name_correctness, print_output, print_output_table
from ragbits.document_search.documents.sources import LocalFileSource


class InnerTestModel(BaseModel):
    id: int
    location: LocalFileSource | None


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
            id=11, name="aa", location=InnerTestModel(id=111, location=LocalFileSource(path=Path("test_location")))
        ),
    ),
    MainTestModel(
        id=2,
        name="B",
        model=OtherTestModel(
            id=22, name="bb", location=InnerTestModel(id=222, location=LocalFileSource(path=Path("test_location")))
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
        columns = {"id": Column(), "model.location.location.path": Column()}
        print_output_table(data, columns)
        mock_print.assert_called_once()
        args, _ = mock_print.call_args_list[0]
        printed_table = args[0]
        assert isinstance(printed_table, Table)
        assert printed_table.columns[0].header == "Id"
        assert printed_table.columns[1].header == "Model Location Location Path"


def test_check_column_name_correctness():
    column = "model.location.location.path"
    fields = {"name": FieldInfo(annotation=str), "model": FieldInfo(annotation=OtherTestModel)}
    try:
        check_column_name_correctness(column, fields)
    except typer.Exit:
        pytest.fail("typer.Exit was raised unexpectedly")


def test_check_column_name_correctness_wrong_field():
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
                check_column_name_correctness(wrong_column, fields)
            mock_print.assert_called_once_with(f"Unknown column: {wrong_column} ({wrong_fragment} not found)")
