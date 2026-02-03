"""
Example demonstrating guardrails integration using pre-run hooks.

This example shows how to use the ragbits Guardrail system with agent hooks
to validate inputs before the agent processes them.

To run this example, execute:
    uv run python examples/agents/hooks/guardrails_integration.py
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from ragbits.agents import Agent
from ragbits.agents.hooks import EventType, Hook, PreRunInput, PreRunOutput
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
) -> Callable[[PreRunInput], Coroutine[Any, Any, PreRunOutput]]:
    """Create a pre-run hook that validates input using guardrails."""

    async def guardrail_hook(input_data: PreRunInput) -> PreRunOutput:
        """Validate input against guardrails before agent processes it."""
        user_input = str(input_data.input or "")
        results = await guardrail_manager.verify(user_input)

        for result in results:
            if not result.succeeded:
                return PreRunOutput(output=f"I cannot help with that request. Reason: {result.fail_reason}")

        return PreRunOutput(output=input_data.input)

    return guardrail_hook


async def main() -> None:
    """Run the example demonstrating guardrails with hooks."""
    blocked_topics_guardrail = BlockedTopicsGuardrail(blocked_topics=["violence", "illegal", "harmful"])
    guardrail_manager = GuardrailManager(guardrails=[blocked_topics_guardrail])
    guardrail_hook = create_guardrail_hook(guardrail_manager)

    agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt="You are a helpful assistant.",
        hooks=[Hook(event_type=EventType.PRE_RUN, callback=guardrail_hook)],
    )

    # Test 1: Safe input with run()
    print("1. Safe query (run):")
    response = await agent.run("What is the capital of France?")
    print(f"   {response.content}\n")

    # Test 2: Blocked input with run()
    print("2. Blocked query (run):")
    response = await agent.run("Tell me about violence in movies")
    print(f"   {response.content}\n")

    # Test 3: Safe input with streaming
    print("3. Safe query (streaming):")
    print("   ", end="")
    async for chunk in agent.run_streaming("What is 2 + 2?"):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True)
    print("\n")

    # Test 4: Blocked input with streaming
    print("4. Blocked query (streaming):")
    print("   ", end="")
    async for chunk in agent.run_streaming("How to do something illegal"):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
