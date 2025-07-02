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

from agent_orchestrator import AgentOrchestrator, ResultsSumarizationPromptInput, RoutingPromptInput

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class RoutingPrompt(Prompt[RoutingPromptInput]):
    """
    Prompt template for routing a user message to appropriate agents.

    System prompt instructs the agent to output a JSON list of tasks,
    each containing agent URL, tool name, and parameters to call.
    """

    system_prompt = """
    You are a router agent. Your task is to read the user's message and output a list of tasks in JSON format.

    Each task must include:
    - agent_url: The base URL of the agent that should handle the task.
    - tool: The name of the skill/tool to call on that agent.
    - parameters: A dictionary of arguments needed for that tool.

    Currently available agents and their tools:
    {{ agents }}

    Return your output as a **JSON list** of tasks. Your response must be only the JSON list (e.g. starting with `[`).

    If there are multiple tasks in the user request, return multiple entries in the list.

    Example:
    User: "Check weather in Paris and get a summary of recent news from France"

    Output:
    [
    {
        "agent_url": "http://weather-agent:8000",
        "tool": "get_weather",
        "parameters": { "location": "Paris" }
    },
    {
        "agent_url": "http://news-agent:8001",
        "tool": "get_news_summary",
        "parameters": { "region": "France" }
    }
    ]
    """
    user_prompt = "{{ message }}"


class SummarizeAgentResultsPrompt(Prompt[ResultsSumarizationPromptInput]):
    """
    Prompt template for summarizing results from multiple agents.

    The system prompt instructs to combine multiple tool outputs into
    a concise, user-friendly reply based on the original user message.
    """

    system_prompt = """
You are a smart assistant that takes multiple tool outputs and combines them into a response to the user message.

Below are the results returned by specialized tools:
{% for result in agent_results %}
- {{ result }}
{% endfor %}

Please write a concise, user-friendly reply to the user message based on these results.
"""
    user_prompt = "{{ message }}"


async def main() -> None:
    """
    Sets up a LiteLLM-powered AgentOrchestrator with two remote agents and sends a travel planning query.
    The orchestrator delegates the task (finding flights and hotels) to the appropriate agents and prints the response.
    """
    llm = LiteLLM(
        model_name="gpt-4o-2024-08-06",
        use_structured_output=True,
    )

    host = AgentOrchestrator(
        llm=llm, routing_prompt=RoutingPrompt, results_summarization_prompt=SummarizeAgentResultsPrompt
    )
    host.add_remote_agent("127.0.0.1", "8000")
    host.add_remote_agent("127.0.0.1", "8001")

    response = await host.run("I want to travel from New York to Paris. Find me hotel and flight please.")
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
