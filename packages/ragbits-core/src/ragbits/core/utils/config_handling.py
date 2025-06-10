from __future__ import annotations

import abc
import asyncio
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, ClassVar, Generic

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.options import OptionsT
from ragbits.core.utils._pyproject import get_config_from_yaml

if TYPE_CHECKING:
    from ragbits.core.config import CoreConfig


class InvalidConfigError(Exception):
    """
    An exception to be raised when an invalid configuration is provided.
    """


class NoPreferredConfigError(InvalidConfigError):
    """
    An exception to be raised when no falling back to preferred configuration is not possible.
    """


def import_by_path(path: str, default_module: ModuleType | None = None) -> Any:  # noqa: ANN401
    """
    Retrieves and returns an object based on the string in the format of "module.submodule:object_name".
    If the first part is omitted, the default module is used.

    Args:
        path: A string representing the path to the object. This can either be a
        path implicitly referencing the default module or a full path (module.submodule:object_name)
        if the object is located in a different module.
        default_module: The default module to search for the object if no specific module
        is provided in the path string.

    Returns:
        Any: The object retrieved from the specified or default module.

    Raises:
        InvalidConfigError: The requested object is not found under the specified module
    """
    if ":" in path:
        try:
            module_stringified, object_stringified = path.split(":")
            module = import_module(module_stringified)
            return getattr(module, object_stringified)
        except AttributeError as err:
            raise InvalidConfigError(f"{object_stringified} not found in module {module_stringified}") from err

    if default_module is None:
        raise InvalidConfigError("Not provided a full path and no default module specified")

    try:
        return getattr(default_module, path)
    except AttributeError as err:
        raise InvalidConfigError(f"{path} not found in module {default_module}") from err


class ObjectConstructionConfig(BaseModel):
    """
    A model for object construction configuration.
    """

    # Path to the class to be constructed
    type: str

    # Configuration details for the class
    config: dict[str, Any] = {}


class WithConstructionConfig(abc.ABC):
    """
    A mixin class that provides methods for initializing classes from configuration.
    """

    # The default module to search for the subclass if no specific module is provided in the type string.
    default_module: ClassVar[ModuleType | None] = None

    # The key under configuration for this class (and its subclasses) can be found.
    configuration_key: ClassVar[str]

    @classmethod
    def subclass_from_config(cls, config: ObjectConstructionConfig) -> Self:
        """
        Initializes the class with the provided configuration. May return a subclass of the class,
        if requested by the configuration.

        Args:
            config: A model containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.

        Raises:
            InvalidConfigError: The class can't be found or is not a subclass of the current class.
        """
        subclass = import_by_path(config.type, cls.default_module)
        if not issubclass(subclass, cls):
            raise InvalidConfigError(f"{subclass} is not a subclass of {cls}")

        return subclass.from_config(config.config)

    @classmethod
    def subclass_from_factory(cls, factory_path: str) -> Self:
        """
        Creates the class using the provided factory function. May return a subclass of the class,
        if requested by the factory. Supports both synchronous and asynchronous factory functions.

        Args:
            factory_path: A string representing the path to the factory function
                in the format of "module.submodule:factory_name".

        Returns:
            An instance of the class initialized with the provided factory function.

        Raises:
            InvalidConfigError: The factory can't be found or the object returned
                is not a subclass of the current class.
        """
        factory = import_by_path(factory_path, cls.default_module)

        if asyncio.iscoroutinefunction(factory):
            try:
                loop = asyncio.get_running_loop()
                obj = asyncio.run_coroutine_threadsafe(factory, loop).result()
            except RuntimeError:
                obj = asyncio.run(factory())
        else:
            obj = factory()

        if not isinstance(obj, cls):
            raise InvalidConfigError(f"The object returned by factory {factory_path} is not an instance of {cls}")

        return obj

    @classmethod
    def preferred_subclass(
        cls, config: CoreConfig, factory_path_override: str | None = None, yaml_path_override: Path | None = None
    ) -> Self:
        """
        Tries to create an instance by looking at project's component preferences, either from YAML
        or from the factory. Takes optional overrides for both, which takes a higher precedence.

        Args:
            config: The CoreConfig instance containing preferred factory and configuration details.
            factory_path_override: A string representing the path to the factory function
                in the format of "module.submodule:factory_name".
            yaml_path_override: A string representing the path to the YAML file containing
                the Ragstack instance configuration.

        Raises:
            InvalidConfigError: If the default factory or configuration can't be found.
        """
        if yaml_path_override:
            preferences = get_config_from_yaml(yaml_path_override)
            if type_config := preferences.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectConstructionConfig.model_validate(type_config))

        if factory_path_override:
            return cls.subclass_from_factory(factory_path_override)

        if preferred_factory := config.component_preference_factories.get(cls.configuration_key):
            return cls.subclass_from_factory(preferred_factory)

        if preferred_config := config.preferred_instances_config.get(cls.configuration_key):
            return cls.subclass_from_config(ObjectConstructionConfig.model_validate(preferred_config))

        raise NoPreferredConfigError(f"Could not find preferred factory or configuration for {cls.configuration_key}")

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        return cls(**config)


class ConfigurableComponent(Generic[OptionsT], WithConstructionConfig):
    """
    Base class for components with configurable options.
    """

    options_cls: type[OptionsT]

    def __init__(self, default_options: OptionsT | None = None) -> None:
        """
        Constructs a new ConfigurableComponent instance.

        Args:
            default_options: The default options for the component.
        """
        self.default_options: OptionsT = default_options or self.options_cls()

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        default_options = config.pop("default_options", None)
        options = cls.options_cls(**default_options) if default_options else None
        return cls(**config, default_options=options)
