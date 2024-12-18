from pathlib import Path
from typing import TypeVar

import typer
from pydantic.alias_generators import to_snake
from rich.console import Console

from ragbits.core.config import core_config
from ragbits.core.utils.config_handling import InvalidConfigError, NoDefaultConfigError, WithConstructionConfig

WithConstructionConfigT = TypeVar("WithConstructionConfigT", bound=WithConstructionConfig)


def get_instance_or_exit(
    cls: type[WithConstructionConfigT],
    type_name: str | None = None,
    yaml_path: Path | None = None,
    factory_path: str | None = None,
    yaml_path_argument_name: str = "--yaml-path",
    factory_path_argument_name: str = "--factory-path",
) -> WithConstructionConfigT:
    """
    Returns an instance of the provided class, initialized using its `subclass_from_defaults` method.
    If the instance can't be created, prints an error message and exits the program.

    Args:
        cls: The class to create an instance of.
        type_name: The name to use in error messages. If None, inferred from the class name.
        yaml_path: Path to a YAML configuration file to use for initialization.
        factory_path: Python path to a factory function to use for initialization.
        yaml_path_argument_name: The name of the argument to use in error messages for the YAML path.
        factory_path_argument_name: The name of the argument to use in error messages for the factory path.
    """
    type_name = type_name or to_snake(cls.__name__).replace("_", " ")
    try:
        return cls.subclass_from_defaults(
            core_config,
            factory_path_override=factory_path,
            yaml_path_override=yaml_path,
        )
    except NoDefaultConfigError as e:
        Console(
            stderr=True
        ).print(f"""You need to provide the [b]{type_name}[/b] instance be used. You can do this by either:
- providing a path to a YAML configuration file with the [b]{yaml_path_argument_name}[/b] option
- providing a Python path to a function that creates a vector store with the [b]{factory_path_argument_name}[/b] option
- setting the default configuration or factory function in your project's [b]pyproject.toml[/b] file""")
        raise typer.Exit(1) from e
    except InvalidConfigError as e:
        Console(stderr=True).print(e)
        raise typer.Exit(1) from e
