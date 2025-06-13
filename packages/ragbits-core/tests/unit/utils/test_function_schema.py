from ragbits.core.utils.function_schema import convert_function_to_function_schema


def get_weather(location: str) -> str:
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.

    Returns:
        The current weather for the given location.
    """
    return "{'location': 'San Francisco', 'temperature': 72, 'unit': 'fahrenheit'}"


def test_convert_function_to_function_schema():
    """Test converting function to function schema"""
    function_schema = convert_function_to_function_schema(get_weather)
    expected_function_schema = {
        "type": "function",
        "function": {
            "name": "get_weather",
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
