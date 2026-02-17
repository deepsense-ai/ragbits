"""
Example demonstrating a post-tool hook for logging outputs from agent tools.

This shows how to log the output returned by downstream agent tools.
Setup: 1 parent agent with 2 expert child agents as tools.
"""

import asyncio

from ragbits.agents import Agent
from ragbits.agents.hooks import EventType, Hook
from ragbits.agents.tool import ToolReturn
from ragbits.core.llms import LiteLLM
from ragbits.core.llms.base import ToolCall


async def log_agent_output(tool_call: ToolCall, tool_return: ToolReturn) -> ToolReturn:
    """Log output from agent tools after they complete."""
    output = tool_return.value

    if isinstance(output, dict):
        output = output.get("content", output)

    print(f"\n{'='*60}\n[{tool_call.name}] output:\n{'-'*60}\n{output}\n{'='*60}")
    return tool_return


async def main() -> None:
    """Run the example."""
    llm = LiteLLM("gpt-4o-mini")

    # Child agent 1: Diet expert
    diet_agent = Agent(
        name="diet_expert",
        description="A nutrition expert who provides diet plans and healthy eating advice",
        llm=llm,
    )

    # Child agent 2: Fitness coach
    fitness_agent = Agent(
        name="fitness_coach",
        description="A personal trainer who creates workout routines and exercise plans",
        llm=llm,
    )

    # Hook to log outputs from both agent tools
    hook = Hook(
        event_type=EventType.POST_TOOL,
        callback=log_agent_output,
        tool_names=["diet_expert", "fitness_coach"],
        priority=1,
    )

    # Parent agent with both expert agents as tools
    parent_agent = Agent(
        name="health_assistant",
        llm=llm,
        tools=[diet_agent, fitness_agent],
        hooks=[hook],
    )

    # Query that should trigger both agent tools
    query = "I want to lose 10kg in 3 months. Can you help me with a plan?"
    print(f"Query: {query}\n")

    response = await parent_agent.run(query)
    print(f"Final Response:\n{response.content}")


if __name__ == "__main__":
    asyncio.run(main())
