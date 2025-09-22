"""
Ragbits Agents Example: Post-Processors

This example demonstrates how to use post-processors with Agent.run() and Agent.run_streaming() methods.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/post_processors.py
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
from types import SimpleNamespace

from ragbits.agents import Agent, AgentResult, PostProcessor, StreamingPostProcessor, ToolCallResult
from ragbits.core.llms.base import BasePrompt, ToolCall, Usage
from ragbits.core.llms.litellm import LiteLLM


class CustomStreamingPostProcessor(StreamingPostProcessor):
    """
    Streaming post-processor that checks for forbidden words.
    """

    def __init__(self, forbidden_words: list[str]) -> None:
        self.forbidden_words = forbidden_words

    async def process_streaming(
        self, chunk: str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage, agent: Agent
    ) -> str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage:
        """
        Process chunks during streaming.
        """
        if isinstance(chunk, str) and chunk.lower().strip() in self.forbidden_words:
            return "[FORBIDDEN_WORD]"
        return chunk


class CustomPostProcessor(PostProcessor):
    """
    Non-streaming post-processor that truncates the content.
    """

    def __init__(self, max_length: int = 200) -> None:
        self.max_length = max_length

    async def process(self, result: AgentResult, agent: Agent) -> AgentResult:
        """
        Process the agent result.
        """
        content = result.content
        content_length = len(content)

        if content_length > self.max_length:
            content = content[: self.max_length]
            content += f"... [TRUNCATED] ({content_length} > {self.max_length} chars)"

        return AgentResult(
            content=content,
            metadata=result.metadata,
            tool_calls=result.tool_calls,
            history=result.history,
            usage=result.usage,
        )


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM("gpt-4.1-mini")
    agent: Agent = Agent(llm=llm, prompt="You are a helpful assistant.")
    stream_result = agent.run_streaming(
        "What is Python?",
        post_processors=[
            CustomStreamingPostProcessor(forbidden_words=["python"]),
            CustomPostProcessor(max_length=200),
        ],
        allow_non_streaming=True,
    )
    async for chunk in stream_result:
        if isinstance(chunk, str):
            print(chunk, end="")
    print(f"\n\nFinal answer:\n{stream_result.content}")


if __name__ == "__main__":
    asyncio.run(main())
