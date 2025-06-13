"""
Ragbits Core Example: Tool use

This example shows how to provide tools and return tool calls from LLM.
We provide a list of tools as additional `tools` parameter to the `llm.generate` method.
Important: this feature does not call provided tools, LLM only decides which tools to call
in order to accomplish a given task.

The script performs the following steps:

    1. Define a function to use as tool for generating weather forecast.
    2. Define input format using Pydantic model.
    3. Implement the `WeatherPrompt` class with a structured system prompt.
    4. Initialize the `LiteLLM` class to generate text.
    5. Return tool calls for generating weather forecast based on the specified location.
    6. Print the returned tool calls.

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

from pydantic import BaseModel

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


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


class WeatherPromptInput(BaseModel):
    """
    Input format for the WeatherPrompt.
    """

    location: str


class WeatherPrompt(Prompt[WeatherPromptInput]):
    """
    Prompt that returns weather for a given location.
    """

    system_prompt = """
    You are a helpful assisstant that responds to user questions about weather.
    """

    user_prompt = """
    Tell me the temperature in {{ location }}.
    """


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    prompt = WeatherPrompt(WeatherPromptInput(location="Paris"))
    response = await llm.generate(prompt, tools=[get_weather])
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
