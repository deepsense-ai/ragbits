import json

from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.a2a.server import create_agent_server
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


def get_flight_info(departure: str, arrival: str) -> str:
    """
    Returns flight information between two locations.

    Args:
        departure: The departure city.
        arrival: The arrival city.

    Returns:
        A JSON string with mock flight details.
    """
    if "new york" in departure.lower() and "paris" in arrival.lower():
        return json.dumps({
            "from": "New York",
            "to": "Paris",
            "flights": [
                {"airline": "British Airways", "departure": "10:00 AM", "arrival": "10:00 PM"},
                {"airline": "Delta", "departure": "1:00 PM", "arrival": "1:00 AM"},
            ],
        })

    return json.dumps({"from": departure, "to": arrival, "flights": "No flight data available"})


class FlightPromptInput(BaseModel):
    """Defines the structured input schema for the flight search prompt."""

    input: str


class FlightPrompt(Prompt[FlightPromptInput]):
    """Prompt for a flight search assistant."""

    system_prompt = """
    You are a helpful travel assistant that finds available flights between two cities.
    """

    user_prompt = """
    {{ input }}
    """


llm = LiteLLM(
    model_name="gpt-4.1",
    use_structured_output=True,
)
flight_agent = Agent(llm=llm, prompt=FlightPrompt, tools=[get_flight_info])


async def main() -> None:
    """Runs the flight agent."""
    flight_agent_card = await flight_agent.get_agent_card(
        name="Flight Info Agent", description="Provides available flight information between two cities.", port=8000
    )
    flight_agent_server = create_agent_server(flight_agent, flight_agent_card, FlightPromptInput)
    await flight_agent_server.serve()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
