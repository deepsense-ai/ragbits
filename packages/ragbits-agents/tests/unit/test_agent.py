import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from ragbits.agents import Agent
from ragbits.agents._main import AgentResult
from ragbits.agents.exceptions import AgentNotAvailableToolSelectedError, AgentNotSupportedToolInResponseError
from ragbits.core.llms.base import LLMResponseWithMetadata, ToolCall, ToolCallsResponse
from ragbits.core.llms.mock import MockLLM
from ragbits.core.prompt.base import BasePrompt, ChatFormat


class MockPrompt(BasePrompt):
    """
    Mock prompt for testing LiteLLM.
    """

    def __init__(self, message: str):
        """
        Constructs a new MockPrompt instance.

        Args:
            message: Message to be used in the prompt.
        """
        self.message = message
        self._conversation_history: list[dict[str, Any]] = []

    @property
    def chat(self) -> ChatFormat:
        """
        Chat content of the prompt.

        Returns:
            Chat content of the prompt.
        """
        return [{"content": self.message, "role": "user"}, *self._conversation_history]

    def add_tool_use_message(self, tool_call_id: str, tool_name: str, tool_arguments: str, tool_call_result: str):
        """
        Add tool call messages to the conversation history.

        Args:
            tool_call_id: id of the tool call.
            tool_name: name of the tool.
            tool_arguments: arguments of the tool.
            tool_call_result: the tool call result.

        Returns:
            Prompt[PromptInputT, PromptOutputT]: The current prompt instance to allow chaining.
        """
        self._conversation_history.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_arguments,
                        },
                    }
                ],
            }
        )
        self._conversation_history.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_call_result})
        return self


def get_weather(location: str) -> str:
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.

    Returns:
        The current weather for the given location.
    """
    if "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


@pytest.fixture
def mock_llm_without_tool_call() -> MockLLM:
    llm = MockLLM()
    llm.generate_with_metadata = AsyncMock()  # type: ignore
    llm.generate_with_metadata.side_effect = [
        LLMResponseWithMetadata(content="Test LLM output", metadata={"usage": "test_usage"}, tool_calls=None),
    ]
    return llm


@pytest.fixture
def mock_llm_with_tool_call() -> MockLLM:
    llm = MockLLM()
    llm.generate_with_metadata = AsyncMock()  # type: ignore
    llm.generate_with_metadata.side_effect = [
        LLMResponseWithMetadata(
            content="Test LLM output",
            metadata={"usage": "test_usage"},
            tool_calls=ToolCallsResponse(
                tool_calls=[
                    ToolCall(
                        tool_name="get_weather",
                        tool_arguments='{"location": "San Francisco"}',  # type: ignore
                        tool_call_id="test",
                        tool_type="function",
                    )
                ]
            ),
        ),
        LLMResponseWithMetadata(
            content="Temperature is 72 fahrenheit",
            metadata={"usage": "test_usage"},
            tool_calls=None,
        ),
    ]
    return llm


@pytest.fixture
def mock_llm_wrong_tool_type() -> MockLLM:
    llm = MockLLM()
    llm.generate_with_metadata = AsyncMock()  # type: ignore
    llm.generate_with_metadata.side_effect = [
        LLMResponseWithMetadata(
            content="Test LLM output",
            metadata={"usage": "test_usage"},
            tool_calls=ToolCallsResponse(
                tool_calls=[
                    ToolCall(
                        tool_name="get_weather",
                        tool_arguments='{"location": "San Francisco"}',  # type: ignore
                        tool_call_id="test",
                        tool_type="tool",
                    )
                ]
            ),
        ),
    ]
    return llm


@pytest.fixture
def mock_prompt_cls() -> type[MockPrompt]:
    return MockPrompt


def test_agent_initialization(mock_llm_without_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    """Test that the Agent initializes correctly."""
    agent = Agent(llm=mock_llm_without_tool_call, prompt=mock_prompt_cls)  # type: ignore
    assert agent.llm is mock_llm_without_tool_call
    assert agent.prompt is mock_prompt_cls
    assert agent.tools_mapping == {}


def test_agent_initialization_with_tools(mock_llm_with_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    """Test that the Agent initializes correctly with tools."""
    agent = Agent(llm=mock_llm_with_tool_call, prompt=mock_prompt_cls, tools=[get_weather])  # type: ignore
    assert agent.llm is mock_llm_with_tool_call
    assert agent.prompt is mock_prompt_cls
    assert "get_weather" in agent.tools_mapping
    assert agent.tools_mapping["get_weather"] is get_weather


@pytest.mark.asyncio
async def test_agent_run_no_tools(mock_llm_without_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    """Test a simple run of the agent without tools."""
    agent = Agent(llm=mock_llm_without_tool_call, prompt=mock_prompt_cls, tools=[get_weather])  # type: ignore
    result = await agent.run("test input")

    assert isinstance(result, AgentResult)
    assert result.content == "Test LLM output"
    assert result.metadata == {"usage": "test_usage"}
    assert result.tool_call is None
    assert result.tool_call_result is None


@pytest.mark.asyncio
async def test_agent_run_tools(mock_llm_with_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    """Test a simple run of the agent without tools."""
    agent = Agent(llm=mock_llm_with_tool_call, prompt=mock_prompt_cls, tools=[get_weather])  # type: ignore
    result = await agent.run("test input")

    assert isinstance(result, AgentResult)
    assert result.content == "Temperature is 72 fahrenheit"
    assert result.metadata == {"usage": "test_usage"}
    assert result.tool_call is None
    assert result.tool_call_result is None


@pytest.mark.asyncio
async def test_agent_iter_no_tools(mock_llm_without_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    agent = Agent(llm=mock_llm_without_tool_call, prompt=mock_prompt_cls)  # type: ignore

    results = []
    async for res in agent.iter("Test LLM output"):
        results.append(res)

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, AgentResult)
    assert result.content == "Test LLM output"
    assert result.metadata == {"usage": "test_usage"}
    assert result.tool_call is None
    assert result.tool_call_result is None


@pytest.mark.asyncio
async def test_agent_iter_with_tools(mock_llm_with_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    agent = Agent(llm=mock_llm_with_tool_call, prompt=mock_prompt_cls, tools=[get_weather])  # type: ignore

    results = []
    async for res in agent.iter("Test LLM output"):
        results.append(res)

    assert len(results) == 2
    assert isinstance(results[0], AgentResult)
    assert results[0].content == "Test LLM output"
    assert results[0].metadata == {"usage": "test_usage"}
    assert results[0].tool_call == ToolCall(
        tool_name="get_weather",
        tool_arguments="{'location': 'San Francisco'}",  # type: ignore
        tool_call_id="test",
        tool_type="function",
    )
    assert results[0].tool_call_result == '{"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"}'
    assert results[1].content == "Temperature is 72 fahrenheit"
    assert results[1].metadata == {"usage": "test_usage"}
    assert results[1].tool_call is None
    assert results[1].tool_call_result is None


@pytest.mark.asyncio
async def test_raises_when_wrong_tool_returned(mock_llm_with_tool_call: MockLLM, mock_prompt_cls: MockPrompt):
    def fake_func() -> None:
        pass

    agent = Agent(llm=mock_llm_with_tool_call, prompt=mock_prompt_cls, tools=[fake_func])  # type: ignore
    with pytest.raises(AgentNotAvailableToolSelectedError):
        await agent.run("test input")


@pytest.mark.asyncio
async def test_raises_when_wrong_tool_type(mock_llm_wrong_tool_type: MockLLM, mock_prompt_cls: MockPrompt):
    agent = Agent(llm=mock_llm_wrong_tool_type, prompt=mock_prompt_cls, tools=[get_weather])  # type: ignore
    with pytest.raises(AgentNotSupportedToolInResponseError):
        await agent.run("test input")
