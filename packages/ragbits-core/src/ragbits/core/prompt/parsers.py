from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

PydanticModelT = TypeVar("PydanticModelT", bound=BaseModel)


class ResponseParsingError(Exception):
    """
    Raised when there is an error parsing an API response.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def int_parser(value: str) -> int:
    """
    Parses a string to an integer.

    Args:
        value: String to parse.

    Returns:
        Integer value of the string.

    Raises:
        ResponseParsingError: If the string cannot be parsed as an integer.
    """
    try:
        return int(value)
    except ValueError as e:
        raise ResponseParsingError(f"Could not parse '{value}' as an integer") from e


def str_parser(value: str) -> str:
    """
    Parses a string.

    Args:
        value: String to parse.

    Returns:
        String value.
    """
    return value


def float_parser(value: str) -> float:
    """
    Parses a string to a float.

    Args:
        value: String to parse.

    Returns:
        Float value of the string.

    Raises:
        ResponseParsingError: If the string cannot be parsed as a float.
    """
    try:
        return float(value)
    except ValueError as e:
        raise ResponseParsingError(f"Could not parse '{value}' as a float") from e


def bool_parser(value: str) -> bool:
    """
    Parses a string to a boolean.

    Args:
        value: String to parse.

    Returns:
        Boolean value of the string.

    Raises:
        ResponseParsingError: If the string cannot be parsed as a boolean.
    """
    value = value.lower()
    if value in {"true", "1", "yes", "y", "TRUE", "YES"}:
        return True
    if value in {"false", "0", "no", "n", "FALSE", "NO"}:
        return False
    raise ResponseParsingError(f"Could not parse '{value}' as a boolean")


def build_pydantic_parser(model: type[PydanticModelT]) -> Callable[[str], PydanticModelT]:
    """
    Builds a parser for a specific Pydantic model.

    Args:
        model: Pydantic model to build the parser for.

    Returns:
        Callable that parses a string to the Pydantic model.

    Raises:
        TypeError: If the model is not a Pydantic model.
    """

    def parser(value: str) -> PydanticModelT:
        """
        Parses a string to a Pydantic model.

        Args:
            value: String to parse.

        Returns:
            Pydantic model instance.

        Raises:
            ResponseParsingError: If the string cannot be parsed as the Pydantic model.
        """
        try:
            return model.model_validate_json(value)
        except ValidationError as e:
            raise ResponseParsingError(f"Could not parse '{value}' as a {model.__name__}") from e

    return parser


DEFAULT_PARSERS: dict[type, Callable[[str], Any]] = {
    int: int_parser,
    str: str_parser,
    float: float_parser,
    bool: bool_parser,
}
