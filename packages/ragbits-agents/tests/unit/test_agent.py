import json

import pytest

from ragbits.agents import Agent
from ragbits.agents._main import AgentResult, ToolCallResult
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.core.prompt.prompt import Prompt


class CustomPrompt(Prompt):
    user_prompt = "Custom test prompt"


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
def llm_without_tool_call() -> MockLLM:
    options = MockLLMOptions(response="Test LLM output")
    return MockLLM(default_options=options)


@pytest.fixture
def llm_with_tool_call() -> MockLLM:
    options = MockLLMOptions(
        response="Temperature is 72 fahrenheit",
        tool_calls=[
            {
                "name": "get_weather",
                "arguments": '{"location": "San Francisco"}',
                "id": "test",
                "type": "function",
            }
        ],
    )
    return MockLLM(default_options=options)


@pytest.fixture
def llm_wrong_tool_type() -> MockLLM:
    options = MockLLMOptions(
        response="Temperature is 72 fahrenheit",
        tool_calls=[
            {
                "name": "get_weather",
                "arguments": '{"location": "San Francisco"}',
                "id": "test",
                "type": "tool",
            }
        ],
    )
    return MockLLM(default_options=options)


async def test_agent_run_no_tools(llm_without_tool_call: MockLLM):
    """Test a simple run of the agent without tools."""
    agent = Agent(
        llm=llm_without_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await agent.run()

    assert isinstance(result, AgentResult)
    assert result.content == "Test LLM output"
    assert result.tool_calls is None


async def test_agent_run_tools(llm_with_tool_call: MockLLM):
    """Test a simple run of the agent without tools."""
    agent = Agent(
        llm=llm_with_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await agent.run()

    assert isinstance(result, AgentResult)
    assert result.content == "Temperature is 72 fahrenheit"
    assert result.tool_calls == [
        ToolCallResult(
            name="get_weather",
            arguments={
                "location": "San Francisco",
            },
            output='{"location": "San Francisco", "temperature": "72", "unit": ' '"fahrenheit"}',
        ),
    ]


async def test_raises_when_wrong_tool_returned(llm_with_tool_call: MockLLM):
    def fake_func() -> None: ...

    agent = Agent(
        llm=llm_with_tool_call,
        prompt=CustomPrompt,
        tools=[fake_func],
    )

    with pytest.raises(AgentToolNotAvailableError):
        await agent.run()


async def test_raises_when_wrong_tool_type(llm_wrong_tool_type: MockLLM):
    agent = Agent(
        llm=llm_wrong_tool_type,
        prompt=CustomPrompt,
        tools=[get_weather],
    )

    with pytest.raises(AgentToolNotSupportedError):
        await agent.run()


async def test_raises_invalid_prompt_input_error_with_none_prompt_and_none_input(llm_without_tool_call: MockLLM):
    agent = Agent(llm=llm_without_tool_call, prompt=None)  # type: ignore

    with pytest.raises(AgentInvalidPromptInputError) as exc_info:
        await agent.run(input=None)

    assert exc_info.value.prompt_type is None
    assert exc_info.value.input_type is None
    assert "Invalid prompt/input combination: prompt=None, input=None" in str(exc_info.value)


async def test_raises_invalid_prompt_input_error_with_invalid_types(llm_without_tool_call: MockLLM):
    agent = Agent(llm=llm_without_tool_call, prompt=123)  # type: ignore

    with pytest.raises(AgentInvalidPromptInputError) as exc_info:
        await agent.run(input={"key": "value"})

    assert exc_info.value.prompt_type == 123
    assert exc_info.value.input_type == {"key": "value"}
    assert "Invalid prompt/input combination" in str(exc_info.value)


async def test_raises_invalid_prompt_input_error_with_list_input(llm_without_tool_call: MockLLM):
    agent = Agent(llm=llm_without_tool_call, prompt=None)  # type: ignore

    with pytest.raises(AgentInvalidPromptInputError) as exc_info:
        await agent.run(input=["item1", "item2"])

    assert exc_info.value.prompt_type is None
    assert exc_info.value.input_type == ["item1", "item2"]
    assert "Invalid prompt/input combination" in str(exc_info.value)
