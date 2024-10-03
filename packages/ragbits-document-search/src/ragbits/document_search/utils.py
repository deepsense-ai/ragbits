from importlib import import_module
from types import ModuleType
from typing import Any


def get_cls_from_config(cls_type: str, default_module: ModuleType) -> Any:
    """
    Retrieves and returns a class based on the given type string. The class can be either in the
    default module or a specified module if provided in the type string.

    Args:
        cls_type: A string representing the class type.
        default_module: The default module to search for the class if no specific module
        is provided in the type string.

    Returns:
        Any: The object retrieved from the specified or default module.
    """
    if ":" in cls_type:
        module_stringified, object_stringified = cls_type.split(":")
        module = import_module(module_stringified)
        return getattr(module, object_stringified)

    return getattr(default_module, cls_type)
