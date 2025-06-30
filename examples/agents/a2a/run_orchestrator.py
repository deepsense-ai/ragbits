"""
Ragbits Agents Example: A2A orchestration

This example demonstrates how to use the `AgentOrchestrator` to route a complex user query
across multiple specialized agents (e.g., hotel and flight). Each agent is hosted as an HTTP server
and can be invoked remotely using the A2A protocol.

The orchestrator automatically routes sub-tasks to the correct agent based on the content of the request.

To run this script
1. Start the hotel agent server in one terminal:

    ```bash
    uv run examples/agents/a2a/hotel_agent.py
    ```

2. Start the flight agent server in a second terminal:
    ```bash
    uv run examples/agents/a2a/flight_agent.py
    ```

3. Then run this orchestrator client script:
    ```bash
    uv run examples/agents/a2a/orchestrator_client.py
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

from ragbits.agents.a2a.agent_orchestrator import AgentOrchestrator
from ragbits.core.llms import LiteLLM


async def main() -> None:
    """
    Sets up a LiteLLM-powered AgentOrchestrator with two remote agents and sends a travel planning query.
    The orchestrator delegates the task (finding flights and hotels) to the appropriate agents and prints the response.
    """
    llm = LiteLLM(
        model_name="gpt-4o-2024-08-06",
        use_structured_output=True,
    )

    host = AgentOrchestrator(llm)
    host.add_remote_agent("127.0.0.1", "8000")
    host.add_remote_agent("127.0.0.1", "8001")

    response = await host.run("I want to travel from New York to Paris. Find me hotel and flight please.")
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
