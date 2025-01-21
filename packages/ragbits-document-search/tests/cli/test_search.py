import sys
from pathlib import Path

from typer.testing import CliRunner

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
