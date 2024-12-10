from pathlib import Path

import pytest

from ragbits.core.utils._pyproject import find_pyproject

projects_dir = Path(__file__).parent.parent / "testprojects"


def test_find_in_current_dir():
    """Test finding a pyproject.toml file in the current directory."""
    found = find_pyproject(projects_dir / "happy_project")
    assert found == projects_dir / "happy_project" / "pyproject.toml"


def test_find_in_parent_dir():
    """Test finding a pyproject.toml file in a parent directory."""
    found = find_pyproject(projects_dir / "happy_project" / "subdirectory")
    assert found == projects_dir / "happy_project" / "pyproject.toml"


def test_find_not_found():
    """Test that it raises FileNotFoundError if the file is not found."""
    with pytest.raises(FileNotFoundError):
        find_pyproject(Path("/"))
