# This file was copied with a few changes from openai-agents-python library
# https://github.com/openai/openai-agents-python/blob/main/src/agents/function_schema.py

import contextlib
import inspect
import logging
from collections.abc import Callable, Generator
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

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


def _build_field(param: inspect.Parameter, ann: Any, description: str | None) -> tuple[Any, Any]:  # noqa: ANN401
    """Build the (annotation, Field) tuple for a single parameter."""
    if param.kind == param.VAR_POSITIONAL:
        # e.g. *args: extend positional args
        if get_origin(ann) is tuple:
            # e.g. def foo(*args: tuple[int, ...]) -> treat as List[int]
            tuple_args = get_args(ann)
            args_of_tuple_with_ellipsis_length = 2
            ann = (
                list[tuple_args[0]]  # type: ignore
                if len(tuple_args) == args_of_tuple_with_ellipsis_length and tuple_args[1] is Ellipsis
                else list[Any]
            )
        else:
            # If user wrote *args: int, treat as List[int]
            ann = list[ann]  # type: ignore
        # Default factory to empty list
        return ann, Field(default_factory=list, description=description)  # type: ignore

    if param.kind == param.VAR_KEYWORD:
        # **kwargs handling
        if get_origin(ann) is dict:
            # e.g. def foo(**kwargs: dict[str, int])
            dict_args = get_args(ann)
            dict_args_to_check_length = 2
            ann = (
                dict[dict_args[0], dict_args[1]]  # type: ignore
                if len(dict_args) == dict_args_to_check_length
                else dict[str, Any]
            )
        else:
            # e.g. def foo(**kwargs: int) -> Dict[str, int]
            ann = dict[str, ann]  # type: ignore
        return ann, Field(default_factory=dict, description=description)  # type: ignore

    if param.default == inspect._empty:
        # Required field
        return ann, Field(..., description=description)

    # Parameter with a default value
    return ann, Field(default=param.default, description=description)


def convert_function_to_function_schema(func: Callable[..., Any]) -> dict:
    """
    Given a python function, extracts a `FuncSchema` from it, capturing the name, description,
    parameter descriptions, and other metadata. Supports nested pydantic models as function arguments.

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

    for name, param in params:
        ann = type_hints.get(name, param.annotation)
        if _is_context_variable(ann):
            continue
        filtered_params.append((name, param))

    # We will collect field definitions for create_model as a dict:
    #   field_name -> (type_annotation, default_value_or_Field(...))
    fields: dict[str, Any] = {}

    for name, param in filtered_params:
        ann = type_hints.get(name, param.annotation)
        if ann == inspect._empty:
            ann = Any
        fields[name] = _build_field(param, ann, param_descs.get(name))

    # 3. Dynamically build a Pydantic model
    dynamic_model = create_model(f"{func_name}_args", __base__=BaseModel, **fields)

    # 4. Build JSON schema from that model
    json_schema = dynamic_model.model_json_schema()

    parameters: dict[str, Any] = {
        "type": "object",
        "properties": json_schema.get("properties", {}),
        "required": json_schema.get("required", []),
    }
    if json_schema.get("$defs"):
        parameters["$defs"] = json_schema["$defs"]

    return {
        "type": "function",
        "function": {
            "name": func_name,
            "description": doc_info["description"] if doc_info else None,
            "parameters": parameters,
        },
    }


def get_context_variable_name(func: Callable[..., Any]) -> str | None:
    """
    Check if a function accepts AgentRunContext as a parameter.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    for name, param in sig.parameters.items():
        ann = type_hints.get(name, param.annotation)
        if _is_context_variable(ann):
            return name

    return None


def _is_context_variable(ann: Any) -> bool:  # noqa: ANN401
    """
    Check if a type annotation is AgentRunContext.
    """
    if ann is None:
        return False

    origin = get_origin(ann)
    if origin is not None:
        if getattr(origin, "__name__", None) == "AgentRunContext":
            return True
        if origin in (Union, UnionType):
            return any(_is_context_variable(arg) for arg in get_args(ann))
        if origin is Annotated:
            args = get_args(ann)
            return bool(args) and _is_context_variable(args[0])

    if getattr(ann, "__name__", None) == "AgentRunContext":
        return True

    return isinstance(ann, str) and "AgentRunContext" in ann
