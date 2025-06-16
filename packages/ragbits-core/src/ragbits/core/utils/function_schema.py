# This file was copied with a few changes from openai-agents-python library
# https://github.com/openai/openai-agents-python/blob/main/src/agents/function_schema.py

import contextlib
import inspect
import logging
from collections.abc import Callable, Generator
from typing import Any, get_args, get_origin, get_type_hints

from griffe import Docstring, DocstringSectionKind
from pydantic import BaseModel, Field, create_model


@contextlib.contextmanager
def _suppress_griffe_logging() -> Generator:
    # Suppresses warnings about missing annotations for params
    logger = logging.getLogger("griffe")
    previous_level = logger.getEffectiveLevel()
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(previous_level)


def _generate_func_documentation(func: Callable[..., Any]) -> dict:
    """
    Extracts metadata from a function docstring, in preparation for sending it to an LLM as a tool.

    Args:
        func: The function to extract documentation from.

    Returns:
        A dict containing the function's name, description, and parameter
        descriptions.
    """
    name = func.__name__
    doc = inspect.getdoc(func)
    if not doc:
        return {"name": name, "description": None, "param_descriptions": None}

    with _suppress_griffe_logging():
        docstring = Docstring(doc, lineno=1, parser="google")
        parsed = docstring.parse()

    description: str | None = next(
        (section.value for section in parsed if section.kind == DocstringSectionKind.text), None
    )

    param_descriptions: dict[str, str] = {
        param.name: param.description
        for section in parsed
        if section.kind == DocstringSectionKind.parameters
        for param in section.value
    }

    return {
        "name": func.__name__,
        "description": description,
        "param_descriptions": param_descriptions or None,
    }


def convert_function_to_function_schema(func: Callable[..., Any]) -> dict:
    """
    Given a python function, extracts a `FuncSchema` from it, capturing the name, description,
    parameter descriptions, and other metadata.

    Args:
        func: The function to extract the schema from.

    Returns:
        A dict containing the function's name, description, parameter descriptions,
        and other metadata.
    """
    # 1. Grab docstring info
    doc_info = _generate_func_documentation(func)
    param_descs = doc_info["param_descriptions"] or {}

    func_name = doc_info["name"] if doc_info else func.__name__

    # 2. Inspect function signature and get type hints
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    params = list(sig.parameters.items())
    filtered_params = []

    if params:
        first_name, first_param = params[0]
        # Prefer the evaluated type hint if available
        ann = type_hints.get(first_name, first_param.annotation)
        filtered_params.append((first_name, first_param))

    # For parameters other than the first, raise error if any use RunContextWrapper.
    for name, param in params[1:]:
        ann = type_hints.get(name, param.annotation)
        filtered_params.append((name, param))

    # We will collect field definitions for create_model as a dict:
    #   field_name -> (type_annotation, default_value_or_Field(...))
    fields: dict[str, Any] = {}

    for name, param in filtered_params:
        ann = type_hints.get(name, param.annotation)
        default = param.default

        # If there's no type hint, assume `Any`
        if ann == inspect._empty:
            ann = Any

        # If a docstring param description exists, use it
        field_description = param_descs.get(name, None)

        # Handle different parameter kinds
        if param.kind == param.VAR_POSITIONAL:
            # e.g. *args: extend positional args
            if get_origin(ann) is tuple:
                # e.g. def foo(*args: tuple[int, ...]) -> treat as List[int]
                args_of_tuple = get_args(ann)
                args_of_tuple_with_ellipsis_length = 2
                ann = (
                    list[args_of_tuple[0]]  # type: ignore
                    if len(args_of_tuple) == args_of_tuple_with_ellipsis_length and args_of_tuple[1] is Ellipsis
                    else list[Any]
                )
            else:
                # If user wrote *args: int, treat as List[int]
                ann = list[ann]  # type: ignore

            # Default factory to empty list
            fields[name] = (
                ann,
                Field(default_factory=list, description=field_description),  # type: ignore
            )

        elif param.kind == param.VAR_KEYWORD:
            # **kwargs handling
            if get_origin(ann) is dict:
                # e.g. def foo(**kwargs: dict[str, int])
                dict_args = get_args(ann)
                dict_args_to_check_length = 2
                ann = (
                    dict[dict_args[0], dict_args[1]]  # type: ignore
                    if len(dict_args) == dict_args_to_check_length
                    else dict[str, Any]
                )  # type: ignore
            else:
                # e.g. def foo(**kwargs: int) -> Dict[str, int]
                ann = dict[str, ann]  # type: ignore

            fields[name] = (
                ann,
                Field(default_factory=dict, description=field_description),  # type: ignore
            )

        elif default == inspect._empty:
            # Required field
            fields[name] = (
                ann,
                Field(..., description=field_description),
            )
        else:
            # Parameter with a default value
            fields[name] = (
                ann,
                Field(default=default, description=field_description),
            )

    # 3. Dynamically build a Pydantic model
    dynamic_model = create_model(f"{func_name}_args", __base__=BaseModel, **fields)

    # 4. Build JSON schema from that model
    json_schema = dynamic_model.model_json_schema()

    return {
        "type": "function",
        "function": {
            "name": func_name,
            "description": doc_info["description"] if doc_info else None,
            "parameters": {
                "type": "object",
                "properties": json_schema.get("properties", {}),
                "required": json_schema.get("required", []),
            },
        },
    }
