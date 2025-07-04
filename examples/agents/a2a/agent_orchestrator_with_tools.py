import asyncio
import json
import threading

import requests
from flight_agent import server as flight_agent_server
from hotel_agent import server as hotel_agent_server
from pydantic import BaseModel
from uvicorn import Server

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt

AGENTS_CARDS = {}


def fetch_agent(host: str, port: int, protocol: str = "http") -> dict:
    url = f"{protocol}://{host}:{port}"
    return requests.get(f"{url}/.well-known/agent.json", timeout=10).json()


for url, port in [("127.0.0.1", "8000"), ("127.0.0.1", "8001")]:
    agent_card = fetch_agent(url, port)
    AGENTS_CARDS[agent_card["name"]] = agent_card

AGENTS_INFO = "\n".join(
    [f"NAME - {name}: {card['description']} DOCS: {card['skills']}" for name, card in AGENTS_CARDS.items()]
)


class OrchestratorPromptInput(BaseModel):
    """Represents a routing prompt input."""

    message: str
    agents: str


class OrchestratorPrompt(Prompt[OrchestratorPromptInput]):
    """
    Prompt template for routing a user message to appropriate agents.

    System prompt instructs the agent to output a JSON list of tasks,
    each containing agent URL, tool name, and parameters to call.
    """

    system_prompt = """
    You are a Trip Planning Agnent.

    To help the user plan their trip, you will need to use the following agents:
    {{ agents }}

    you can use `execute_agent` tool to interact with remote agents to take action. You must provide agent name that
    will be prefixed with NAME and parameters as a dictionary to this function

    """
    user_prompt = "{{ message }}"


def execute_agent(agent_name: str, parameters: dict) -> str:
    """
    Executes a specified agent with the given parameters.

    Args:
        agent_name: Name of the agent to execute
        parameters: Parameters to pass to the agent

    Returns:
        JSON string of the execution result
    """
    payload = {"params": parameters}
    raw_response = requests.post(AGENTS_CARDS[agent_name]["url"], json=payload, timeout=10)
    raw_response.raise_for_status()

    response = raw_response.json()
    result_data = response["result"]

    tool_calls = [
        {"name": call["name"], "arguments": call["arguments"], "output": call["result"]}
        for call in result_data.get("tool_calls", [])
    ] or None

    return json.dumps(
        {
            "status": "success",
            "agent_name": agent_name,
            "result": {
                "content": result_data["content"],
                "metadata": result_data.get("metadata", {}),
                "tool_calls": tool_calls,
            },
        }
    )


async def wait_for_server_to_start(server: Server, check_interval: float = 0.001) -> None:
    """
    Starts the given server in a background thread and asynchronously waits until it signals readiness.

    Args:
        server: The server instance to run. Expected to have a `.run()` method and `.started` attribute.
        check_interval: Time in seconds between readiness checks (default: 0.001).

    Returns:
        None
    """
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        await asyncio.sleep(check_interval)


async def main() -> None:
    """
    Sets up a LiteLLM-powered AgentOrchestrator with two remote agents and sends a travel planning query.
    The orchestrator delegates the task (finding flights and hotels) to the appropriate agents and prints the response.
    """
    await asyncio.gather(*(wait_for_server_to_start(server) for server in [hotel_agent_server, flight_agent_server]))

    llm = LiteLLM(
        model_name="gpt-4o-2024-08-06",
        use_structured_output=True,
    )

    agent = Agent(llm=llm, prompt=OrchestratorPrompt, tools=[execute_agent], keep_history=True)

    while True:
        user_input = input("USER: ")
        result = await agent.run(OrchestratorPromptInput(message=user_input, agents=AGENTS_INFO))
        print("ASSISTANT:", result.content)


if __name__ == "__main__":
    asyncio.run(main())
