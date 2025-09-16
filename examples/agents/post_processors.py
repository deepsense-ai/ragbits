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

from ragbits.agents import Agent, AgentResult, BasePostProcessor
from ragbits.core.llms.litellm import LiteLLM


class CustomStreamingProcessor(BasePostProcessor):
    def __init__(self, forbidden_words: list[str]) -> None:
        self.forbidden_words = forbidden_words

    @property
    def supports_streaming(self) -> bool:
        return True

    async def process_streaming(self, chunk, agent: "Agent"):
        if isinstance(chunk, str):
            if chunk.lower().strip() in self.forbidden_words:
                return "[FORBIDDEN_WORD]"
        return chunk


class CustomNonStreamingProcessor(BasePostProcessor):
    def __init__(self, max_length: int = 200) -> None:
        self.max_length = max_length

    @property
    def supports_streaming(self) -> bool:
        return False

    async def process(self, result: "AgentResult", agent: "Agent") -> "AgentResult":
        content = result.content
        content_length = len(content)

        if content_length > self.max_length:
            content = content[:self.max_length] 
            content += f"... [TRUNCATED] ({content_length} > {self.max_length} chars)"

        return AgentResult(
            content=content,
            metadata=result.metadata,
            tool_calls=result.tool_calls,
            history=result.history,
            usage=result.usage,
        )


async def main():
    llm = LiteLLM("gpt-3.5-turbo")
    agent = Agent(llm=llm, prompt="You are a helpful assistant.")
    post_processors = [
        CustomStreamingProcessor(forbidden_words=["python"]),
        CustomNonStreamingProcessor(max_length=200),
    ]
    stream_result = agent.run_streaming("What is Python?", post_processors=post_processors, allow_non_streaming=True)
    async for chunk in stream_result:
        if isinstance(chunk, str):
            print(chunk, end="")
    print(f"\nFinal answer:\n{stream_result.content}")


if __name__ == "__main__":
    asyncio.run(main())
