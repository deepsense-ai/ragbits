import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ragbits.core.config import CoreConfig, import_modules_from_config
from ragbits.core.utils._pyproject import get_config_instance
from ragbits.document_search.cli import ds_app, state

projects_dir = Path(__file__).parent.parent / "unit" / "testprojects"

# So that we can import the factory functions
sys.path.append(str(projects_dir))

# Path to the factory function that creates the test document search instance
factory_path = "project_with_instance_factory.factories:create_document_search_instance_223"


@pytest.fixture
def add_custom_source_to_path():
    original_path = sys.path.copy()
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if current_dir not in sys.path:
        sys.path.append(current_dir)

    yield

    sys.path = original_path


@pytest.mark.parametrize(
    ("pattern", "num_expected"),
    [
        ("*", 4),
        ("test?.txt", 3),
        ("test??.txt", 1),
        ("test*.txt", 4),
    ],
)
def test_ingest(pattern: str, num_expected: int) -> None:
    runner = CliRunner(mix_stderr=False)
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple test files
        test_files = [
            (Path(temp_dir) / "test1.txt", "First test content"),
            (Path(temp_dir) / "test2.txt", "Second test content"),
            (Path(temp_dir) / "test3.txt", "Third test content"),
            (Path(temp_dir) / "test33.txt", "Third test content"),
        ]
        for file_path, content in test_files:
            file_path.write_text(content)
        source_pattern = f"local://{temp_dir}/{pattern}"
        result = runner.invoke(
            ds_app,
            ["--factory-path", factory_path, "ingest", source_pattern],
        )
    assert result.exit_code == 0
    assert len(asyncio.run(state.document_search.vector_store.list())) == num_expected  # type: ignore


def test_ingest_fails_with_custom_source_without_module_import() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "CustomSource.txt"
        content = "Test content"
        file_path.write_text(content)

        source_path = f"custom_cli_protocol://{file_path}"
        result = runner.invoke(
            ds_app,
            ["--factory-path", factory_path, "ingest", source_path],
        )

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "Unsupported protocol: custom_cli_protocol." in str(result.exception)


def test_ingest_succeeds_with_custom_source_with_module_import(add_custom_source_to_path) -> None:  # noqa: ANN001
    core_config = get_config_instance(CoreConfig)
    core_config.modules_to_import = ["custom_cli_source"]
    import_modules_from_config(core_config)

    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "CustomSource.txt"
        content = "Test content"
        file_path.write_text(content)

        source_path = f"custom_cli_protocol://{file_path}"
        result = runner.invoke(
            ds_app,
            ["--factory-path", factory_path, "ingest", source_path],
        )

    assert result.exit_code == 0
    assert len(asyncio.run(state.document_search.vector_store.list())) == 1  # type: ignore
