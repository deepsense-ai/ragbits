"""
Ragbits Core Example: Tool Use with LLM

This example demonstrates how to provide tools and return tool calls from LLM.
We provide a list of tools as additional `tools` parameter to the `llm.generate` method.

Important: this feature does not call provided tools, LLM only decides which tools to call
in order to accomplish a given task.

To run the script, execute the following command:

    ```bash
    uv run examples/core/llms/tool_use.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///

import asyncio
import json

from ragbits.core.llms import LiteLLM


def get_weather(location: str) -> str:
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.

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


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06")
    response = await llm.generate("What's the temperature in San Francisco?", tools=[get_weather])
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
