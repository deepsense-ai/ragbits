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


def get_cls_from_config(cls_path: str, default_module: ModuleType | None) -> Any:  # noqa: ANN401
    """
    Retrieves and returns a class based on the given type string. The class can be either in the
    default module or a specified module if provided in the type string.

    Args:
        cls_path: A string representing the path to the class or object. This can either be a
        path implicitly referencing the default module or a full path (module.submodule:ClassName)
        if the class is located in a different module.
        default_module: The default module to search for the class if no specific module
        is provided in the type string.

    Returns:
        Any: The object retrieved from the specified or default module.
    """
    if ":" in cls_path:
        try:
            module_stringified, object_stringified = cls_path.split(":")
            module = import_module(module_stringified)
            return getattr(module, object_stringified)
        except AttributeError as err:
            raise InvalidConfigError(f"Class {object_stringified} not found in module {module_stringified}") from err

    if default_module is None:
        raise InvalidConfigError("Given type string does not contain a module and no default module provided")

    try:
        return getattr(default_module, cls_path)
    except AttributeError as err:
        raise InvalidConfigError(f"Class {cls_path} not found in module {default_module}") from err


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
        """
        subclass = get_cls_from_config(config.type, cls.default_module)
        if not issubclass(subclass, cls):
            raise InvalidConfigError(f"{subclass} is not a subclass of {cls}")

        return subclass.from_config(config.config)

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
