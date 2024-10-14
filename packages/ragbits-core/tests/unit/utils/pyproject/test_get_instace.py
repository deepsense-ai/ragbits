from pathlib import Path

from pydantic import BaseModel

from ragbits.core.utils._pyproject import get_config_instance

projects_dir = Path(__file__).parent / "testprojects"


class HappyProjectConfig(BaseModel):
    foo: str
    is_happy: bool
    happiness_level: int


class PartialHappyProjectConfig(BaseModel):
    foo: str
    is_happy: bool


class OptionalHappyProjectConfig(BaseModel):
    foo: str = "bar"
    is_happy: bool = True
    happiness_level: int = 100


def test_get_config_instance():
    """Test getting Pydantic model instance from pyproject.toml file."""
    config = get_config_instance(
        HappyProjectConfig,
        subproject="happy-project",
        current_dir=projects_dir / "happy_project",
    )

    assert config == HappyProjectConfig(foo="bar", is_happy=True, happiness_level=100)


def test_get_config_instance_additional_fields():
    """Test that unknown fields are ignored."""
    config = get_config_instance(
        PartialHappyProjectConfig,
        subproject="happy-project",
        current_dir=projects_dir / "happy_project",
    )

    assert config == PartialHappyProjectConfig(foo="bar", is_happy=True)


def test_get_config_instance_optional_fields():
    """Test that optional fields are filled with default values if not present in the file."""
    config = get_config_instance(
        OptionalHappyProjectConfig,
        subproject="happy-project",
        current_dir=projects_dir / "happy_project",
    )

    assert config == OptionalHappyProjectConfig(foo="bar", is_happy=True, happiness_level=100)


def test_get_config_instance_no_file():
    """Test getting config when the pyproject.toml file is not found (wich no required fields)."""
    config = get_config_instance(
        OptionalHappyProjectConfig,
        subproject="happy-project",
        current_dir=Path("/"),
    )

    assert config == OptionalHappyProjectConfig()
