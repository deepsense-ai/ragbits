"""
Example demonstrating guardrails using pre-run and post-run hooks.

Pre-run hook: Validates input before agent processes it.
Post-run hook: Validates output and triggers rerun with correction if needed.
"""

import asyncio

from ragbits.agents import Agent
from ragbits.agents.hooks import EventType, Hook, PostRunInput, PostRunOutput, PreRunInput, PreRunOutput
from ragbits.core.llms import LiteLLM

BLOCKED_TOPICS = ["violence", "illegal"]


async def input_guardrail(input_data: PreRunInput) -> PreRunOutput:
    """Block requests containing forbidden topics."""
    user_input = str(input_data.input or "").lower()

    for topic in BLOCKED_TOPICS:
        if topic in user_input:
            return PreRunOutput(output=f"I cannot help with topics related to {topic}.")

    return PreRunOutput(output=input_data.input)


async def output_guardrail(input_data: PostRunInput) -> PostRunOutput:
    """Validate output and request correction if it contains forbidden content."""
    content = str(input_data.result.content).lower()

    for topic in BLOCKED_TOPICS:
        if topic in content:
            return PostRunOutput(
                result=input_data.result,
                rerun=True,
                correction_prompt=f"Your response mentioned '{topic}'. Please rephrase without that topic.",
            )

    return PostRunOutput(result=input_data.result)


async def main() -> None:
    """Run the example."""
    agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt="You are a helpful assistant.",
        hooks=[
            Hook(event_type=EventType.PRE_RUN, callback=input_guardrail),
            Hook(event_type=EventType.POST_RUN, callback=output_guardrail),
        ],
    )

    # Test with safe input
    response = await agent.run("What is the capital of France?")
    print(f"Safe query response: {response.content}\n")

    # Test with blocked input
    response = await agent.run("Tell me about violence in movies")
    print(f"Blocked query response: {response.content}")


if __name__ == "__main__":
    asyncio.run(main())
