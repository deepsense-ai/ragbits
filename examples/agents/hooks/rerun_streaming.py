"""
Example demonstrating post-run hook triggering rerun in streaming mode.

The hook validates output and requests a rerun with correction prompt if needed.
"""

import asyncio

from ragbits.agents import Agent
from ragbits.agents.hooks import EventType, Hook, PostRunInput, PostRunOutput
from ragbits.core.llms import LiteLLM


async def validate_and_rerun(input_data: PostRunInput) -> PostRunOutput:
    """Validate output and trigger rerun if it's too short."""
    content = str(input_data.result.content)

    if len(content) < 1000:
        return PostRunOutput(
            result=input_data.result,
            rerun=True,
            correction_prompt="Your response was too brief. Please provide a more detailed explanation.",
        )

    return PostRunOutput(result=input_data.result)


async def main() -> None:
    """Run the example."""
    agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt="You are a helpful assistant. Be concise unless asked otherwise.",
        hooks=[Hook(event_type=EventType.POST_RUN, callback=validate_and_rerun)],
    )

    query = "What is Python?"

    print(f"Query: {query}\n")
    print("Streaming response:")

    async for chunk in agent.run_streaming(query):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
