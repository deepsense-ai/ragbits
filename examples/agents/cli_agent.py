"""
Ragbits Agents Example: CLI agent

This example demonstrates how to expose an agent via the ragbits CLI, allowing
it to be run interactively from the command line with conversation history.

To expose the CLI Agent simply run:
    ```bash
    uv run ragbits agents run examples.agents.cli_agent:test_agent
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-agents",
# ]
# ///

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM


def get_current_weather(location: str) -> str:
    """
    Get the current weather in a specific location.

    Args:
        location: The location to get weather for

    Returns:
        Weather information for the location
    """
    # Mock weather data
    weather_data = {
        "London": "Rainy, 15°C",
        "Paris": "Sunny, 22°C",
        "New York": "Cloudy, 18°C",
        "Tokyo": "Sunny, 25°C",
    }

    return weather_data.get(location, f"Weather data not available for {location}")


# Create a simple test agent
llm = LiteLLM(model_name="gpt-3.5-turbo")

test_agent = Agent(
    llm=llm,
    prompt="You are a helpful assistant that can help with weather information and general questions.",
    tools=[get_current_weather],
    keep_history=True,
)
