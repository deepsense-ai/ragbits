"""
Ragbits Agents Example: Tool use

This example shows how to use agent with tools.
We provide a single method as a tool to the agent and expect it to call it when answering query.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/tool_use.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-agents",
# ]
# ///
import asyncio
import json

from pydantic import BaseModel

from ragbits.agents import Agent
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
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "10", "unit": "celsius"})
    elif "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
    else:
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
    You are a helpful assistant that responds to user questions about weather.
    """

    user_prompt = """
    Tell me the temperature in {{ location }}.
    """


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    agent = Agent(llm=llm, prompt=WeatherPrompt, tools=[get_weather])
    response = await agent.run(WeatherPromptInput(location="Paris"))
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
