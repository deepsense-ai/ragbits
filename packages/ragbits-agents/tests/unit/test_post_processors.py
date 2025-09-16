import pytest
from ragbits.agents.post_processors.base import BasePostProcessor
from ragbits.agents import Agent, AgentResult, AgentRunContext
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.agents.exceptions import AgentInvalidPostProcessorError


class MockNonStreamingPostProcessor(BasePostProcessor):
    def __init__(self, append_content: str = " - processed"):
        self.append_content = append_content

    async def process(self, result: AgentResult, agent: Agent) -> AgentResult:
        result.content += self.append_content
        return result


class MockStreamingPostProcessor(BasePostProcessor):
    def __init__(self, append_content: str = " - streamed"):
        self.append_content = append_content

    @property
    def supports_streaming(self) -> bool:
        return True

    async def process_streaming(self, chunk, agent: Agent):
        if isinstance(chunk, str):
            return chunk + self.append_content
        return chunk


@pytest.fixture
def mock_llm() -> MockLLM:
    options = MockLLMOptions(response="Initial response")
    return MockLLM(default_options=options)


@pytest.mark.asyncio
async def test_non_streaming_post_processor(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    post_processor = MockNonStreamingPostProcessor()

    result = await agent.run(post_processors=[post_processor])

    assert result.content == "Initial response - processed"


@pytest.mark.asyncio
async def test_streaming_post_processor(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    post_processor = MockStreamingPostProcessor()

    result = agent.run_streaming(post_processors=[post_processor])
    async for chunk in result:
        if isinstance(chunk, str):
            assert chunk.endswith(" - streamed")


@pytest.mark.asyncio
async def test_non_streaming_processor_in_streaming_mode_raises_error(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    post_processor = MockNonStreamingPostProcessor()

    with pytest.raises(AgentInvalidPostProcessorError):
        result = agent.run_streaming(post_processors=[post_processor])
        async for _ in result:
            pass


@pytest.mark.asyncio
async def test_non_streaming_processor_in_streaming_mode_with_allow_non_streaming(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    post_processor = MockNonStreamingPostProcessor()

    result = agent.run_streaming(post_processors=[post_processor], allow_non_streaming=True)

    async for _ in result:
        pass

    assert result.content == "Initial response - processed"


@pytest.mark.asyncio
async def test_streaming_and_non_streaming_processors(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    non_streaming_processor = MockNonStreamingPostProcessor()
    streaming_processor = MockStreamingPostProcessor()

    result = agent.run_streaming(
        post_processors=[streaming_processor, non_streaming_processor],
        allow_non_streaming=True
    )

    async for _ in result:
        pass

    assert result.content == "Initial response - streamed - processed"


@pytest.mark.asyncio
async def test_streaming_processor_always_runs_before_non_streaming_processor(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    non_streaming_processor = MockNonStreamingPostProcessor()
    streaming_processor = MockStreamingPostProcessor()

    result = agent.run_streaming(
        post_processors=[streaming_processor, non_streaming_processor],
        allow_non_streaming=True
    )
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed - processed"

    result = agent.run_streaming(
        post_processors=[non_streaming_processor, streaming_processor],
        allow_non_streaming=True
    )
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed - processed"

@pytest.mark.asyncio
async def test_multiple_non_streaming_processors_order(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    non_streaming_processor_1 = MockNonStreamingPostProcessor(append_content=" - processed 1")
    non_streaming_processor_2 = MockNonStreamingPostProcessor(append_content=" - processed 2")

    result = await agent.run(
        post_processors=[non_streaming_processor_2, non_streaming_processor_1]
    )

    assert result.content == "Initial response - processed 2 - processed 1"

@pytest.mark.asyncio
async def test_multiple_streaming_processors_order(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    streaming_processor_1 = MockStreamingPostProcessor(append_content=" - streamed 1")
    streaming_processor_2 = MockStreamingPostProcessor(append_content=" - streamed 2")

    result = agent.run_streaming(
        post_processors=[streaming_processor_2, streaming_processor_1],
    )
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed 2 - streamed 1"

@pytest.mark.asyncio
async def test_multiple_streaming_and_non_streaming_processors_order(mock_llm):
    agent = Agent(llm=mock_llm, prompt="Test prompt")
    streaming_processor_1 = MockStreamingPostProcessor(append_content=" - streamed 1")
    streaming_processor_2 = MockStreamingPostProcessor(append_content=" - streamed 2")
    non_streaming_processor_1 = MockNonStreamingPostProcessor(append_content=" - processed 1")
    non_streaming_processor_2 = MockNonStreamingPostProcessor(append_content=" - processed 2")

    result = agent.run_streaming(
        post_processors=[non_streaming_processor_2, streaming_processor_1, non_streaming_processor_1, streaming_processor_2],
        allow_non_streaming=True
    )
    async for _ in result:
        pass

    assert result.content == "Initial response - streamed 1 - streamed 2 - processed 2 - processed 1"
