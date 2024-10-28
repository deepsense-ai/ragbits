import enum
from pathlib import Path
from typing import Any, TypeVar

import tomli
from pydantic import BaseModel

from ragbits.core.llms.base import LLMType


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
    current_dir = current_dir or Path.cwd()

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
    current_dir = current_dir or Path.cwd()

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
    Creates an instance of pydantic model loaded with the configuration from pyproject.toml.

    Args:
        model (Type[BaseModel]): The pydantic model to instantiate.
        subproject (str, optional): The subproject to get the configuration for, defaults to giving entire
            ragbits configuration.
        current_dir (Path, optional): The directory to start searching for the pyproject.toml file. Defaults to the
            current working directory

    Returns:
        ConfigModelT: The model instance loaded with the configuration
    """
    current_dir = current_dir or Path.cwd()

    config = get_ragbits_config(current_dir)
    if subproject:
        config = config.get(subproject, {})
    if "default_llm_factories" in config:
        config["default_llm_factories"] = {
            _resolve_enum_member(k): v for k, v in config["default_llm_factories"].items()
        }
    return model(**config)


def _resolve_enum_member(enum_string: str) -> enum.Enum:
    try:
        return LLMType(enum_string)
    except ValueError as err:
        raise ValueError("Unsupported LLMType value provided in default_llm_factories in pyproject.toml") from err
