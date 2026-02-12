"""
Ragbits Agents Example: Streaming custom events from tools

This example demonstrates how to define a tool that emits custom events that can be handled in the streaming
loop of an agent.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/stream_events_form_tools.py
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
from collections.abc import AsyncGenerator

from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.tool import ToolReturn
from ragbits.core.llms import LiteLLM


class MyEvent(BaseModel):
    """Custom event that we want to stream from an agent"""

    name: str
    description: str


async def my_tool() -> AsyncGenerator[ToolReturn | str | int | MyEvent]:
    """
    Fetches revenue data (in thousands of dollars) for the given year and displays it as a Markdown table.
    """
    yield "My Event 1"
    yield 2
    yield MyEvent(name="My Event 3", description="Another event that will be yielded in an agent")
    yield ToolReturn(value="Successfully called my_tool! Your lucky number is 7")


async def main() -> None:
    """Run the agent with streaming events from the tools"""
    llm = LiteLLM(model_name="gpt-4o")
    agent = Agent(llm, prompt="Call my_tool for every answer", tools=[my_tool])
    result = agent.run_streaming("Hello, please call my_tool and tell me what is the number it returned!")
    async for event in result:
        print(event)
    print()
    print("Tool events:", result.tool_events)


if __name__ == "__main__":
    asyncio.run(main())
