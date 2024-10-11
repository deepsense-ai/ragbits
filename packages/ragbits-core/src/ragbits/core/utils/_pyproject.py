from pathlib import Path
from typing import Any, TypeVar

import tomli
from pydantic import BaseModel


def _get_current_dir(current_dir: Path | None = None) -> Path:
    """
    Returns the current directory if `current_dir` is None.

    Args:
        current_dir (Path, optional): The directory to check. Defaults to None.

    Returns:
        Path: The current directory.
    """
    return current_dir or Path.cwd()


def find_pyproject(current_dir: Path | None = None) -> Path:
    """
    Find the pyproject.toml file in the current directory or any of its parents.

    Args:
        current_dir (Path, optional): The directory to start searching from. Defaults to the
            current working directory.

    Returns:
        Path: The path to the found pyproject.toml file.

    Raises:
        FileNotFoundError: If the pyproject.toml file is not found.
    """
    current_dir = _get_current_dir(current_dir)

    possible_dirs = [current_dir, *current_dir.parents]
    for possible_dir in possible_dirs:
        pyproject = possible_dir / "pyproject.toml"
        if pyproject.exists():
            return pyproject
    raise FileNotFoundError("pyproject.toml not found")


def get_ragbits_config(current_dir: Path | None = None) -> dict[str, Any]:
    """
    Get the ragbits configuration from the project's pyproject.toml file.

    Only configuration from the [tool.ragbits] section is returned.
    If the project doesn't include any ragbits configuration, an empty dictionary is returned.

    Args:
        current_dir (Path, optional): The directory to start searching for the pyproject.toml file. Defaults to the
            current working directory.

    Returns:
        dict: The ragbits configuration.
    """
    current_dir = _get_current_dir(current_dir)

    try:
        pyproject = find_pyproject(current_dir)
    except FileNotFoundError:
        # Projects are not required to use pyproject.toml
        # No file just means no configuration
        return {}

    with pyproject.open("rb") as f:
        pyproject_data = tomli.load(f)
    return pyproject_data.get("tool", {}).get("ragbits", {})


ConfigModelT = TypeVar("ConfigModelT", bound=BaseModel)


def get_config_instance(
    model: type[ConfigModelT], subproject: str | None = None, current_dir: Path | None = None
) -> ConfigModelT:
    """
    Creates an instace of pydantic model loaded with the configuration from pyproject.toml.

    Args:
        model (Type[BaseModel]): The pydantic model to instantiate.
        subproject (str, optional): The subproject to get the configuration for, defaults to giving entire
            ragbits configuration.
        current_dir (Path, optional): The directory to start searching for the pyproject.toml file. Defaults to the
            current working directory

    Returns:
        ConfigModelT: The model instance loaded with the configuration
    """
    current_dir = _get_current_dir(current_dir)

    config = get_ragbits_config(current_dir)
    print(config)
    if subproject:
        config = config.get(subproject, {})
    return model(**config)
