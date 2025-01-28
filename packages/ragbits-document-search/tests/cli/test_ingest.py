import asyncio
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ragbits.document_search.cli import ds_app, state

projects_dir = Path(__file__).parent.parent / "unit" / "testprojects"

# So that we can import the factory functions
sys.path.append(str(projects_dir))

# Path to the factory function that creates the test document search instance
factory_path = "project_with_instance_factory.factories:create_document_search_instance_223"


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
        source_pattern = f"file://{temp_dir}/{pattern}"
        result = runner.invoke(
            ds_app,
            ["--factory-path", factory_path, "ingest", source_pattern],
        )
    assert result.exit_code == 0
    assert len(asyncio.run(state.document_search.vector_store.list())) == num_expected  # type: ignore
