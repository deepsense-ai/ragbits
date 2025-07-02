import json

from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.a2a.server import create_agent_app, run_agent_server
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
        return json.dumps(
            {
                "from": "New York",
                "to": "Paris",
                "flights": [
                    {"airline": "British Airways", "departure": "10:00 AM", "arrival": "10:00 PM"},
                    {"airline": "Delta", "departure": "1:00 PM", "arrival": "1:00 AM"},
                ],
            }
        )
    elif "los angeles" in departure.lower() and "tokyo" in arrival.lower():
        return json.dumps(
            {
                "from": "Los Angeles",
                "to": "Tokyo",
                "flights": [
                    {"airline": "ANA", "departure": "8:00 AM", "arrival": "12:00 PM"},
                    {"airline": "JAL", "departure": "4:00 PM", "arrival": "8:00 AM"},
                ],
            }
        )
    else:
        return json.dumps({"from": departure, "to": arrival, "flights": "No flight data available"})


class FlightPromptInput(BaseModel):
    """Defines the structured input schema for the flight search prompt."""

    departure: str
    arrival: str


class FlightPrompt(Prompt[FlightPromptInput]):
    """Prompt for a flight search assistant."""

    system_prompt = """
    You are a helpful travel assistant that finds available flights between two cities.
    """

    user_prompt = """
    I need to fly from {{ departure }} to {{ arrival }}. What flights are available?
    """


llm = LiteLLM(
    model_name="gpt-4o-2024-08-06",
    use_structured_output=True,
)
agent = Agent(llm=llm, prompt=FlightPrompt, tools=[get_flight_info])
agent_card = agent.get_agent_card(
    name="Flight Info Agent",
    description="Provides available flight information between two cities.",
)

app = create_agent_app(agent, agent_card, FlightPromptInput)
run_agent_server(agent, agent_card, FlightPromptInput)
