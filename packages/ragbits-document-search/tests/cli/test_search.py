import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from ragbits.cli import app as root_app
from ragbits.cli import autoregister
from ragbits.cli.state import CliState, cli_state
from ragbits.document_search.cli import ds_app

projects_dir = Path(__file__).parent.parent / "unit" / "testprojects"

# So that we can import the factory functions
sys.path.append(str(projects_dir))

# Path to the factory function that creates the test document search instance
factory_path = "project_with_instance_factory.factories:create_document_search_instance_with_documents"


def test_no_object():
    """
    Test the document-search CLI command with no DocumentSearch object.

    Args:
        cli_runner: A CLI runner fixture.
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(ds_app, ["search"])
    assert "You need to provide the document search instance to be used" in result.stderr


def test_search():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        ds_app,
        ["--factory-path", factory_path, "search", "example query"],
    )
    assert result.exit_code == 0
    assert "Foo document" in result.stdout
    assert "Bar document" in result.stdout
    assert "Baz document" in result.stdout


def test_search_limit():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        ds_app,
        ["--factory-path", factory_path, "search", "--k", "2", "example query"],
    )
    assert result.exit_code == 0
    assert "Foo document" in result.stdout
    assert "Bar document" in result.stdout
    assert "Baz document" not in result.stdout


def test_search_columns():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        ds_app,
        ["--factory-path", factory_path, "search", "example query", "--columns", "document_meta,location"],
    )
    assert result.exit_code == 0
    assert "Foo document" not in result.stdout
    assert "Bar document" not in result.stdout
    assert "Baz document" not in result.stdout
    assert "page_number=" in result.stdout
    assert "coordinates=" in result.stdout
    assert "<DocumentType.TXT: 'txt'>" in result.stdout


def test_search_nested_columns():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        ds_app,
        [
            "--factory-path",
            factory_path,
            "search",
            "example query",
            "--columns",
            "location,location.coordinates,location.page_number",
        ],
    )
    assert result.exit_code == 0
    print(result.stdout)
    assert "Foo document" not in result.stdout
    assert "Bar document" not in result.stdout
    assert "Baz document" not in result.stdout
    assert "Location" in result.stdout
    assert "Location Coordinates" in result.stdout
    assert "Location Page Number" in result.stdout


def test_search_columns_non_existent():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        ds_app,
        [
            "--factory-path",
            factory_path,
            "search",
            "example query",
            "--columns",
            "document_meta,location,non_existent",
        ],
    )
    assert result.exit_code == 1
    assert "Unknown column: non_existent" in result.stderr


def test_search_nested_columns_non_existent():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        ds_app,
        [
            "--factory-path",
            factory_path,
            "search",
            "example query",
            "--columns",
            "document_meta,location,location.non_existent",
        ],
    )
    assert result.exit_code == 1
    assert "Unknown column: location.non_existent" in result.stderr


def test_search_json():
    autoregister()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        root_app,
        [
            "--output",
            "json",
            "document-search",
            "--factory-path",
            factory_path,
            "search",
            "example query",
        ],
    )
    assert result.exit_code == 0
    elements = json.loads(result.stdout)
    assert len(elements) == 3
    assert elements[0]["key"] == "Foo document"
    assert elements[1]["key"] == "Bar document"
    assert elements[2]["key"] == "Baz document"

    # Reset the output type to the default value so it doesn't affect other tests
    cli_state.output_type = CliState.output_type
