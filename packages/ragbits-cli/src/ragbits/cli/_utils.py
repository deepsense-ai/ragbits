from pathlib import Path
from typing import Protocol, TypeVar

import typer
from pydantic.alias_generators import to_snake
from rich.console import Console

from ragbits.core.config import CoreConfig, core_config
from ragbits.core.utils.config_handling import InvalidConfigError, NoPreferredConfigError, WithConstructionConfig

WithConstructionConfigT_co = TypeVar("WithConstructionConfigT_co", bound=WithConstructionConfig, covariant=True)


# Using a Protocol instead of simply typing the `cls` argument to `get_instance_or_exit`
# as `type[WithConstructionConfigT]` in order to workaround the issue of mypy not allowing abstract classes
# to be used as types: https://github.com/python/mypy/issues/4717
class WithConstructionConfigProtocol(Protocol[WithConstructionConfigT_co]):
    @classmethod
    def preferred_subclass(
        cls, config: CoreConfig, factory_path_override: str | None = None, yaml_path_override: Path | None = None
    ) -> WithConstructionConfigT_co: ...


def get_instance_or_exit(
    cls: WithConstructionConfigProtocol[WithConstructionConfigT_co],
    type_name: str | None = None,
    yaml_path: Path | None = None,
    factory_path: str | None = None,
    config_override: CoreConfig | None = None,
    yaml_path_argument_name: str = "--yaml-path",
    factory_path_argument_name: str = "--factory-path",
) -> WithConstructionConfigT_co:
    """
    Returns an instance of the provided class, initialized using its `preferred_subclass` method.
    If the instance can't be created, prints an error message and exits the program.

    Args:
        cls: The class to create an instance of.
        type_name: The name to use in error messages. If None, inferred from the class name.
        yaml_path: Path to a YAML configuration file to use for initialization.
        factory_path: Python path to a factory function to use for initialization.
        yaml_path_argument_name: The name of the argument to use in error messages for the YAML path.
        config_override: A config instance to be used
        factory_path_argument_name: The name of the argument to use in error messages for the factory path.
    """
    if not isinstance(cls, type):
        raise TypeError(f"get_instance_or_exit expects the `cls` argument to be a class, got {cls}")

    type_name = type_name or to_snake(cls.__name__).replace("_", " ")
    try:
        return cls.preferred_subclass(
            config_override or core_config,
            factory_path_override=factory_path,
            yaml_path_override=yaml_path,
        )
    except NoPreferredConfigError as e:
        Console(
            stderr=True
        ).print(f"""You need to provide the [b]{type_name}[/b] instance to be used. You can do this by either:
- providing a path to a YAML configuration file with the [b]{yaml_path_argument_name}[/b] option
- providing a Python path to a function that creates a vector store with the [b]{factory_path_argument_name}[/b] option
- setting the preferred {type_name} configuration in your project's [b]pyproject.toml[/b] file
  (see https://ragbits.deepsense.ai/how-to/project/component_preferences/ for more information)""")
        raise typer.Exit(1) from e
    except InvalidConfigError as e:
        Console(stderr=True).print(e)
        raise typer.Exit(1) from e
