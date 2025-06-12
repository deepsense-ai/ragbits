# How-To: Use Tool Calling with LLMs in Ragbits

This guide will walk you through providing external tools to use by LLMs. This feature enables LLMs to return which of the provided tools to call and with which arguments in order to accomplish a task given in the prompt.

## Define tools

Tools for LLMs can be defined as Python functions or as JSON schemas.

=== "Python function"

    ```python
    def get_weather(location: str) -> str:
        """
        Returns the current weather for a given location.

        Args:
            location: The location to get the weather for.
        """
    ```

=== "JSON schema"

    ```python
    {
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
    ```

For convenience lets use Python function notation.

```python
import json

def get_weather(location: str, units: str | None = None) -> str:
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.
        units: The units to use for the weather information.

    Returns:
        The current weather for the given location.
    """
    match location.lower():
        case "tokyo":
            return json.dumps({"location": "Tokyo", "temperature": "10", "unit": "celsius"})
        case "san francisco":
            return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
        case "paris":
            return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
        case _:
            return json.dumps({"location": location, "temperature": "unknown"})
```

Tools can be passed to the LLM as an optional generation argument. If LLM decides to use tools, then the tool calls will be returned directly as a response and there will be no text output.

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06")
    response = await llm.generate("What's the temperature in San Francisco?", tools=[get_weather])
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

!!! info
    Using tools in local LLMs is not supported - any tools passed as arguments to local LLMs are ignored.

## Stream tool calls

Tools can also be streamed from the LLM. If LLM decides to use multiple tools, they will be returned in the iterator one by one.

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06")
    response = llm.generate_streaming("What's the temperature in San Francisco?", tools=[get_weather])
    async for chunk in response:
        print(chunk)

if __name__ == "__main__":
    asyncio.run(main())
```
