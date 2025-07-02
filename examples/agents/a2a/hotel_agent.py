import json

from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.a2a.server import create_agent_app, create_agent_server
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


def get_hotel_recommendations(city: str) -> str:
    """
    Returns hotel recommendations for a given city and date range.

    Args:
        city: The destination city.

    Returns:
        A JSON string with mock hotel details.
    """
    city_lower = city.lower()

    if "paris" in city_lower:
        return json.dumps(
            {
                "city": "Paris",
                "hotels": [
                    {"name": "Hotel Le Meurice", "rating": 5, "price_per_night": 450},
                    {"name": "Hotel Regina Louvre", "rating": 4, "price_per_night": 300},
                ],
            }
        )
    elif "rome" in city_lower:
        return json.dumps(
            {
                "city": "Rome",
                "hotels": [
                    {"name": "Hotel Eden", "rating": 5, "price_per_night": 400},
                    {"name": "Hotel Artemide", "rating": 4, "price_per_night": 250},
                ],
            }
        )
    else:
        return json.dumps(
            {
                "city": city,
                "hotels": "No hotel data available",
            }
        )


class HotelPromptInput(BaseModel):
    """Defines the structured input for the hotel recommendation prompt."""

    city: str


class HotelPrompt(Prompt[HotelPromptInput]):
    """Prompt for a hotel recommendation assistant."""

    system_prompt = """
    You are a helpful travel assistant that recommends hotels based on the city and travel dates.
    """

    user_prompt = """
    I'm planning a trip to {{ city }}. Can you recommend some hotels?
    """


llm = LiteLLM(
    model_name="gpt-4o-2024-08-06",
    use_structured_output=True,
)

agent = Agent(llm=llm, prompt=HotelPrompt, tools=[get_hotel_recommendations])

agent_card = agent.get_agent_card(
    name="Hotel Recommendation Agent", description="Recommends hotels for a given city and travel dates.", port="8001"
)

app = create_agent_app(agent, agent_card, HotelPromptInput)
server = create_agent_server(agent, agent_card, HotelPromptInput)
