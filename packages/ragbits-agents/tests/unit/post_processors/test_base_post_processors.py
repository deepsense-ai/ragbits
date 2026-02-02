from types import SimpleNamespace

import pytest

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.post_processors.base import StreamingPostProcessor
from ragbits.core.llms.base import BasePrompt, ToolCall, Usage
from ragbits.core.llms.mock import MockLLM, MockLLMOptions


class MockStreamingPostProcessor(StreamingPostProcessor):
    def __init__(self, append_content: str = " - streamed"):
        self.append_content = append_content

    async def process_streaming(
        self,
        chunk: str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest,
        agent: Agent,
    ):
        if isinstance(chunk, str):
            return chunk + self.append_content
        return chunk


@pytest.fixture
def mock_llm() -> MockLLM:
    options = MockLLMOptions(response="Initial response")
    return MockLLM(default_options=options)


@pytest.mark.asyncio
async def test_streaming_post_processor(mock_llm: MockLLM):
    agent: Agent = Agent(llm=mock_llm, prompt="Test prompt")
    post_processor = MockStreamingPostProcessor()

    result = agent.run_streaming(post_processors=[post_processor])
    async for chunk in result:
        if isinstance(chunk, str):
            assert chunk.endswith(" - streamed")


@pytest.mark.asyncio
async def test_multiple_streaming_processors_order(mock_llm: MockLLM):
    agent: Agent = Agent(llm=mock_llm, prompt="Test prompt")
    streaming_processor_1 = MockStreamingPostProcessor(append_content=" - streamed 1")
    streaming_processor_2 = MockStreamingPostProcessor(append_content=" - streamed 2")

    result = agent.run_streaming(
        post_processors=[streaming_processor_2, streaming_processor_1],
    )
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed 2 - streamed 1"
