"""
Example demonstrating guardrails integration using pre-run and on-event hooks.

This example shows how to use the ragbits Guardrail system with agent hooks
to validate inputs before the agent processes them and how to use ON_EVENT
hooks to transform streaming output in real-time.

To run this example, execute:
    uv run python examples/agents/hooks/guardrails_integration.py
"""

import asyncio

from ragbits.agents import Agent
from ragbits.agents._main import AgentOptions, AgentRunContext
from ragbits.agents.hooks import EventType, Hook, OnEventCallback, PreRunCallback
from ragbits.agents.hooks.types import StreamingEvent
from ragbits.core.llms import LiteLLM
from ragbits.guardrails.base import Guardrail, GuardrailManager, GuardrailVerificationResult


class BlockedTopicsGuardrail(Guardrail):
    """Guardrail that blocks requests containing forbidden topics."""

    def __init__(self, blocked_topics: list[str]) -> None:
        self.blocked_topics = blocked_topics

    async def verify(self, input_to_verify: str) -> GuardrailVerificationResult:
        """Check if input contains any blocked topics."""
        input_lower = str(input_to_verify).lower()

        for topic in self.blocked_topics:
            if topic in input_lower:
                return GuardrailVerificationResult(
                    guardrail_name=self.__class__.__name__,
                    succeeded=False,
                    fail_reason=f"Input contains blocked topic: {topic}",
                )

        return GuardrailVerificationResult(
            guardrail_name=self.__class__.__name__,
            succeeded=True,
            fail_reason=None,
        )


def create_guardrail_hook(
    guardrail_manager: GuardrailManager,
) -> PreRunCallback:
    """Create a pre-run hook that validates input using guardrails."""

    async def guardrail_hook(
        input: str | None,
        options: AgentOptions,
        context: AgentRunContext,
    ) -> str | None:
        """Validate input against guardrails before agent processes it."""
        user_input = str(input or "")
        results = await guardrail_manager.verify(user_input)

        for result in results:
            if not result.succeeded:
                return f"I cannot help with that request. Reason: {result.fail_reason}"

        return input

    return guardrail_hook


def create_upper_words_hook(words: list[str]) -> OnEventCallback:
    """Create an ON_EVENT hook that upper-cases specified words in streaming text chunks."""

    async def upper_words_hook(event: StreamingEvent) -> StreamingEvent | None:
        if isinstance(event, str):
            result = event
            for word in words:
                result = result.replace(word, word.upper())
            return result
        return event

    return upper_words_hook


async def main() -> None:
    """Run the example demonstrating guardrails with hooks."""
    blocked_topics_guardrail = BlockedTopicsGuardrail(blocked_topics=["politics", "religion"])
    guardrail_manager = GuardrailManager(guardrails=[blocked_topics_guardrail])
    guardrail_hook = create_guardrail_hook(guardrail_manager)
    upper_hook = create_upper_words_hook(["founded", "party"])

    agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt="You are a helpful assistant.",
        hooks=[
            Hook(event_type=EventType.PRE_RUN, callback=guardrail_hook),
            Hook(event_type=EventType.ON_EVENT, callback=upper_hook),
        ],
    )

    # Test 1: Safe input with run()
    print("1. Safe query (run):")
    response = await agent.run("What is the capital of France?")
    print(f"\t{response.content}\n")

    # Test 2: Blocked input with run()
    print("2. Blocked query (run):")
    response = await agent.run("Tell me about religion in ancient Rome?")
    print(f"\t{response.content}\n")

    # Test 3: Safe input with streaming
    print("3. Safe query (streaming):\n\t", end="")
    async for chunk in agent.run_streaming("What is 2 + 2?"):
        if isinstance(chunk, str):
            print(chunk, end="")

    # Test 4: Blocked input with streaming — pre-run hook blocks, on-event hook upper-cases the rejection message
    print("\n\n4. On event upper-casing (streaming):\n\t", end="")
    async for chunk in agent.run_streaming("What are the main political parties in the US?"):
        if isinstance(chunk, str):
            print(chunk, end="")


if __name__ == "__main__":
    asyncio.run(main())
