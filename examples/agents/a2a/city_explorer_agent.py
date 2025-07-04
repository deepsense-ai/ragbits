from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.a2a.server import create_agent_server
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class CityExplorerPromptInput(BaseModel):
    """Defines the structured input schema for the city explorer prompt."""

    city: str


class CityExplorerPrompt(Prompt[CityExplorerPromptInput]):
    """Prompt for a city explorer assistant."""

    system_prompt = """
    You are a helpful travel assistant that gathers and synthesizes city information from the internet.
    To gather information call mcp fetch server with the URL to the city's wikipedia page.
    Then synthesize the information into a concise summary.

    e.g
    https://en.wikipedia.org/wiki/London
    https://en.wikipedia.org/wiki/Paris
    """

    user_prompt = """
    Tell me about {{ city }}.
    """


class MCPServerStdio:
    pass

async def main() -> None:
    async with MCPServerStdio(
            params={
                "command": "python",
                "args": ["-m", "mcp-server-fetch"],
            }
        ) as server:
        llm = LiteLLM(
            model_name="gpt-4o-2024-08-06",
            use_structured_output=True,
        )
        city_explorer_agent = Agent(llm=llm, prompt=CityExplorerPrompt, mcp_servers=[server])

        city_explorer_agent_card = city_explorer_agent.get_agent_card(
            name="City Explorer Agent",
            description="Provides information about a city.",
        )
        city_explorer_server = create_agent_server(city_explorer_agent, city_explorer_agent_card, CityExplorerPromptInput)
        await city_explorer_server.serve()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
