"""
Ragbits Agents Example: Multi-agent setup (QA agent + Time agent)

This example demonstrates how to build a setup with two agents:
1. A Time Agent that returns the current time for a given location.
2. A QA Agent that answers user questions and can delegate to the Time Agent.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/downstream_agents_streaming.py
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

from ragbits.agents import Agent, AgentOptions, AgentRunContext, DownstreamAgentResult
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


def get_time(location: str) -> str:
    """
    Returns the current time for a given location.

    Args:
        location: The location to get the time for.

    Returns:
        The current time for the given location.
    """
    loc = location.lower()
    if "tokyo" in loc:
        return json.dumps({"location": "Tokyo", "time": "10:00 AM"})
    elif "paris" in loc:
        return json.dumps({"location": "Paris", "time": "04:00 PM"})
    elif "san francisco" in loc:
        return json.dumps({"location": "San Francisco", "time": "07:00 PM"})
    else:
        return json.dumps({"location": location, "time": "unknown"})


class TimePromptInput(BaseModel):
    """Input schema for the TimePrompt, containing the target location."""

    location: str


class TimePrompt(Prompt[TimePromptInput]):
    """
    Provides instructions for generating the current time in a user-specified
    location.
    """

    system_prompt = """
    You are a helpful assistant that tells the current time in a given city.
    """
    user_prompt = """
    What time is it in {{ location }}?
    """


llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
time_agent = Agent(
    name="time_agent",
    description="Returns current time for a given location",
    llm=llm,
    prompt=TimePrompt,
    tools=[get_time],
    default_options=AgentOptions(max_total_tokens=1000, max_turns=5),
)


class QAPromptInput(BaseModel):
    """Input schema for the QA agent, containing a natural-language question."""

    question: str


class QAPrompt(Prompt[QAPromptInput]):
    """
    Guides the agent to respond to user questions.
    """

    system_prompt = """
    You are a helpful assistant that responds to user questions.
    """
    user_prompt = """
    {{ question }}.
    """


llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
qa_agent = Agent(
    name="qa_agent",
    llm=llm,
    prompt=QAPrompt,
    tools=[time_agent],
    default_options=AgentOptions(max_total_tokens=1000, max_turns=5),
)


async def main() -> None:
    """
    Run the QA agent with downstream streaming enabled.

    The QA agent processes a sample question ("What time is it in Paris?") and delegates to
    the Time Agent when necessary. Streamed results from both agents are printed in real time,
    tagged by the agent that produced them.
    """
    context = AgentRunContext(stream_downstream_events=True)

    async for chunk in qa_agent.run_streaming(QAPromptInput(question="What time is it in Paris?"), context=context):
        if isinstance(chunk, DownstreamAgentResult):
            agent_name = context.get_agent(chunk.agent_id).name
            print(f"[{agent_name}] {chunk.item}")
        else:
            print(f"[{qa_agent.name}] {chunk}")


if __name__ == "__main__":
    asyncio.run(main())
