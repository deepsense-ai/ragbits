from types import SimpleNamespace

import pytest

from ragbits.agents import Agent, AgentOptions, AgentResult, AgentRunContext, ToolCallResult
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.exceptions import AgentInvalidPostProcessorError
from ragbits.agents.post_processors.base import PostProcessor, StreamingPostProcessor
from ragbits.core.llms.base import BasePrompt, ToolCall, Usage
from ragbits.core.llms.mock import MockLLM, MockLLMOptions


class MockPostProcessor(PostProcessor):
    def __init__(self, append_content: str = " - processed"):
        self.append_content = append_content

    async def process(
        self,
        result: AgentResult,
        agent: Agent,
        options: AgentOptions | None = None,
        context: AgentRunContext | None = None,
    ) -> AgentResult:
        result.content += self.append_content
        return result


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
async def test_non_streaming_post_processor(mock_llm: MockLLM):
    post_processor = MockPostProcessor()
    agent: Agent = Agent(llm=mock_llm, prompt="Test prompt", post_processors=[post_processor])

    result = await agent.run()

    assert result.content == "Initial response - processed"


@pytest.mark.asyncio
async def test_streaming_post_processor(mock_llm: MockLLM):
    post_processor = MockStreamingPostProcessor()
    agent: Agent = Agent(llm=mock_llm, prompt="Test prompt", post_processors=[post_processor])

    result = agent.run_streaming()
    async for chunk in result:
        if isinstance(chunk, str):
            assert chunk.endswith(" - streamed")


@pytest.mark.asyncio
async def test_non_streaming_processor_in_streaming_mode_raises_error(mock_llm: MockLLM):
    post_processor = MockPostProcessor()
    agent: Agent = Agent(llm=mock_llm, prompt="Test prompt", post_processors=[post_processor])

    with pytest.raises(AgentInvalidPostProcessorError):
        await anext(agent.run_streaming())  # type: ignore  # ignore type-checking to test raising the error


@pytest.mark.asyncio
async def test_non_streaming_processor_in_streaming_mode_with_allow_non_streaming(mock_llm: MockLLM):
    post_processor = MockPostProcessor()
    agent: Agent = Agent(llm=mock_llm, prompt="Test prompt", post_processors=[post_processor])

    result = agent.run_streaming(allow_non_streaming=True)

    async for _ in result:
        pass

    assert result.content == "Initial response - processed"


@pytest.mark.asyncio
async def test_streaming_and_non_streaming_processors(mock_llm: MockLLM):
    non_streaming_processor = MockPostProcessor()
    streaming_processor = MockStreamingPostProcessor()
    agent: Agent = Agent(
        llm=mock_llm, prompt="Test prompt", post_processors=[streaming_processor, non_streaming_processor]
    )

    result = agent.run_streaming(allow_non_streaming=True)

    async for _ in result:
        pass

    assert result.content == "Initial response - streamed - processed"


@pytest.mark.asyncio
async def test_streaming_processor_always_runs_before_non_streaming_processor(mock_llm: MockLLM):
    non_streaming_processor = MockPostProcessor()
    streaming_processor = MockStreamingPostProcessor()

    agent1: Agent = Agent(
        llm=mock_llm, prompt="Test prompt", post_processors=[streaming_processor, non_streaming_processor]
    )
    result = agent1.run_streaming(allow_non_streaming=True)
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed - processed"

    agent2: Agent = Agent(
        llm=mock_llm, prompt="Test prompt", post_processors=[non_streaming_processor, streaming_processor]
    )
    result = agent2.run_streaming(allow_non_streaming=True)
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed - processed"


@pytest.mark.asyncio
async def test_multiple_non_streaming_processors_order(mock_llm: MockLLM):
    non_streaming_processor_1 = MockPostProcessor(append_content=" - processed 1")
    non_streaming_processor_2 = MockPostProcessor(append_content=" - processed 2")
    agent: Agent = Agent(
        llm=mock_llm, prompt="Test prompt", post_processors=[non_streaming_processor_2, non_streaming_processor_1]
    )

    result = await agent.run()

    assert result.content == "Initial response - processed 2 - processed 1"


@pytest.mark.asyncio
async def test_multiple_streaming_processors_order(mock_llm: MockLLM):
    streaming_processor_1 = MockStreamingPostProcessor(append_content=" - streamed 1")
    streaming_processor_2 = MockStreamingPostProcessor(append_content=" - streamed 2")
    agent: Agent = Agent(
        llm=mock_llm, prompt="Test prompt", post_processors=[streaming_processor_2, streaming_processor_1]
    )

    result = agent.run_streaming()
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed 2 - streamed 1"


@pytest.mark.asyncio
async def test_multiple_streaming_and_non_streaming_processors_order(mock_llm: MockLLM):
    streaming_processor_1 = MockStreamingPostProcessor(append_content=" - streamed 1")
    streaming_processor_2 = MockStreamingPostProcessor(append_content=" - streamed 2")
    non_streaming_processor_1 = MockPostProcessor(append_content=" - processed 1")
    non_streaming_processor_2 = MockPostProcessor(append_content=" - processed 2")

    agent: Agent = Agent(
        llm=mock_llm,
        prompt="Test prompt",
        post_processors=[
            non_streaming_processor_2,
            streaming_processor_1,
            non_streaming_processor_1,
            streaming_processor_2,
        ],
    )

    result = agent.run_streaming(allow_non_streaming=True)
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed 1 - streamed 2 - processed 2 - processed 1"
