import asyncio
import json

import requests
from pydantic import BaseModel

from ragbits.agents import Agent, ToolCallResult
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import Prompt

AGENTS_CARDS = {}


def fetch_agent(host: str, port: int, protocol: str = "http") -> dict:  # type: ignore
    """Fetches the agent card from the given host and port."""
    url = f"{protocol}://{host}:{port}"
    return requests.get(f"{url}/.well-known/agent.json", timeout=10).json()


for url, port in [("127.0.0.1", "8000"), ("127.0.0.1", "8001")]:
    agent_card = fetch_agent(url, port)
    AGENTS_CARDS[agent_card["name"]] = agent_card

AGENTS_INFO = "\n".join([
    f"name: {name}, description: {card['description']}, skills: {card['skills']}" for name, card in AGENTS_CARDS.items()
])


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
    You are a Trip Planning Agent.

    To help the user plan their trip, you will need to use the following agents:
    {{ agents }}

    you can use `execute_agent` tool to interact with remote agents to take action.

    """
    user_prompt = "{{ message }}"


def execute_agent(agent_name: str, query: str) -> str:
    """
    Executes a specified agent with the given parameters.

    Args:
        agent_name: Name of the agent to execute
        query: The query to pass to the agent

    Returns:
        JSON string of the execution result
    """
    payload = {"params": {"input": query}}
    raw_response = requests.post(AGENTS_CARDS[agent_name]["url"], json=payload, timeout=60)
    raw_response.raise_for_status()

    response = raw_response.json()
    result_data = response["result"]

    tool_calls = [
        {"name": call["name"], "arguments": call["arguments"], "output": call["result"]}
        for call in result_data.get("tool_calls", [])
    ] or None

    return json.dumps({
        "status": "success",
        "agent_name": agent_name,
        "result": {
            "content": result_data["content"],
            "metadata": result_data.get("metadata", {}),
            "tool_calls": tool_calls,
        },
    })


async def main() -> None:
    """
    Sets up a LiteLLM-powered AgentOrchestrator with two remote agents and sends a travel planning query.
    The orchestrator delegates the task (finding flights and hotels) to the appropriate agents and prints the response.
    """
    llm = LiteLLM(
        model_name="gpt-4.1",
        use_structured_output=True,
    )

    agent = Agent(llm=llm, prompt=OrchestratorPrompt, tools=[execute_agent], keep_history=True)

    while True:
        user_input = input("\nUSER: ")
        print("ASSISTANT:")
        async for chunk in agent.run_streaming(OrchestratorPromptInput(message=user_input, agents=AGENTS_INFO)):
            match chunk:
                case ToolCall():
                    print(f"Tool call: {chunk.name} with arguments {chunk.arguments}")
                case ToolCallResult():
                    print(f"Tool call result: {chunk.result[:100]}...")
                case _:
                    print(chunk, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
