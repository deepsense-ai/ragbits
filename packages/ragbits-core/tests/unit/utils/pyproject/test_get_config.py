from pathlib import Path

from ragbits.core.utils._pyproject import get_ragbits_config

projects_dir = Path(__file__).parent.parent / "testprojects"


def test_get_config():
    """Test getting config from pyproject.toml file."""
    config = get_ragbits_config(projects_dir / "happy_project")

    assert config == {
        "lorem": "ipsum",
        "happy-project": {
            "foo": "bar",
            "is_happy": True,
            "happiness_level": 100,
        },
        "project_base_path": str(projects_dir / "happy_project"),
    }


def test_get_config_no_file():
    """Test getting config when the pyproject.toml file is not found."""
    config = get_ragbits_config(Path("/"))

    assert config == {}
