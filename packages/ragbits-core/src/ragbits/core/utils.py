from importlib import import_module
from types import ModuleType
from typing import Any


def get_cls_from_config(cls_path: str, default_module: ModuleType) -> Any:
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
        module_stringified, object_stringified = cls_path.split(":")
        module = import_module(module_stringified)
        return getattr(module, object_stringified)

    return getattr(default_module, cls_path)
