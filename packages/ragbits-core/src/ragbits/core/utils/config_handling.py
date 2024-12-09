import abc
from importlib import import_module
from types import ModuleType
from typing import Any, ClassVar

from pydantic import BaseModel
from typing_extensions import Self


class InvalidConfigError(Exception):
    """
    An exception to be raised when an invalid configuration is provided.
    """


def import_by_path(path: str, default_module: ModuleType | None) -> Any:  # noqa: ANN401
    """
    Retrieves and returns an object based on the string in the format of "module.submodule:object_name".
    If the first part is ommited, the default module is used.

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


class ObjectContructionConfig(BaseModel):
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

    @classmethod
    def subclass_from_config(cls, config: ObjectContructionConfig) -> Self:
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
        if requested by the factory.

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
        obj = factory()
        if not isinstance(obj, cls):
            raise InvalidConfigError(f"The object returned by factory {factory_path} is not an instance of {cls}")
        return obj

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
