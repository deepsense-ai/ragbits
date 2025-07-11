from collections.abc import Callable

import pytest

from ragbits.agents import AgentRunContext
from ragbits.core.utils.function_schema import convert_function_to_function_schema, get_context_variable_name


def get_weather(location: str, context: AgentRunContext) -> str:  # noqa: D417
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.

    Returns:
        The current weather for the given location.
    """
    return "{'location': 'San Francisco', 'temperature': 72, 'unit': 'fahrenheit'}"


def get_weather_no_context(location: str) -> str:
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.

    Returns:
        The current weather for the given location.
    """
    return "{'location': 'San Francisco', 'temperature': 72, 'unit': 'fahrenheit'}"


@pytest.mark.parametrize("function", [get_weather, get_weather_no_context])
def test_convert_function_to_function_schema(function: Callable):
    """Test converting function to function schema"""
    function_schema = convert_function_to_function_schema(function)
    expected_function_schema = {
        "type": "function",
        "function": {
            "name": function.__name__,
            "description": "Returns the current weather for a given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "description": "The location to get the weather for.",
                        "title": "Location",
                        "type": "string",
                    }
                },
                "required": ["location"],
            },
        },
    }
    assert function_schema == expected_function_schema


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        (get_weather, "context"),
        (get_weather_no_context, None),
    ],
)
def test_get_context_variable_name(function: Callable, expected: str | None):
    """Test getting the context variable name"""
    assert get_context_variable_name(function) == expected
