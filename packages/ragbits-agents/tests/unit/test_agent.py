import json
from collections.abc import Callable
from typing import cast

import pytest
from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents._main import AgentOptions, AgentResult, AgentResultStreaming, ToolCallResult
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
    AgentMaxTurnsExceededError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.core.prompt.prompt import Prompt


class WeatherInput(BaseModel):
    location: str
    date: str


class WeatherPrompt(Prompt[WeatherInput, str]):
    system_prompt = "You are a weather assistant"
    user_prompt = "What's the weather like in {{location}} on {{date}}?"


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


@pytest.fixture
def llm_multiple_tool_calls() -> MockLLM:
    options = MockLLMOptions(
        response="Final response after multiple tool calls",
        tool_calls=[
            {
                "name": "get_weather",
                "arguments": '{"location": "San Francisco"}',
                "id": "test1",
                "type": "function",
            },
            {
                "name": "get_weather",
                "arguments": '{"location": "New York"}',
                "id": "test2",
                "type": "function",
            },
            {
                "name": "get_weather",
                "arguments": '{"location": "London"}',
                "id": "test3",
                "type": "function",
            },
        ],
    )
    return MockLLM(default_options=options)


async def _run(agent: Agent, input: str | BaseModel | None = None, options: AgentOptions | None = None) -> AgentResult:
    return await agent.run(input, options)


async def _run_streaming(
    agent: Agent, input: str | BaseModel | None = None, options: AgentOptions | None = None
) -> AgentResultStreaming:
    result = agent.run_streaming(input, options)
    async for _chunk in result:
        pass
    return result


@pytest.mark.parametrize(("method", "result_type"), [(_run, AgentResult), (_run_streaming, AgentResultStreaming)])
async def test_agent_run_no_tools(llm_without_tool_call: MockLLM, method: Callable, result_type: type):
    """Test a simple run of the agent without tools."""
    agent = Agent(
        llm=llm_without_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await method(agent)

    assert isinstance(result, result_type)
    result = cast(AgentResult, result)
    assert result.content == "Test LLM output"
    assert result.tool_calls is None


@pytest.mark.parametrize(("method", "result_type"), [(_run, AgentResult), (_run_streaming, AgentResultStreaming)])
async def test_agent_run_tools(llm_with_tool_call: MockLLM, method: Callable, result_type: type):
    """Test a simple run of the agent without tools."""
    agent = Agent(
        llm=llm_with_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await method(agent)

    assert isinstance(result, result_type)
    result = cast(AgentResult, result)
    assert result.content == "Temperature is 72 fahrenheit"
    assert result.tool_calls == [
        ToolCallResult(
            id="test",
            name="get_weather",
            arguments={
                "location": "San Francisco",
            },
            result='{"location": "San Francisco", "temperature": "72", "unit": ' '"fahrenheit"}',
        ),
    ]


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_raises_when_wrong_tool_returned(llm_with_tool_call: MockLLM, method: Callable):
    def fake_func() -> None: ...

    agent = Agent(
        llm=llm_with_tool_call,
        prompt=CustomPrompt,
        tools=[fake_func],
    )

    with pytest.raises(AgentToolNotAvailableError):
        await method(agent)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_raises_when_wrong_tool_type(llm_wrong_tool_type: MockLLM, method: Callable):
    agent = Agent(
        llm=llm_wrong_tool_type,
        prompt=CustomPrompt,
        tools=[get_weather],
    )

    with pytest.raises(AgentToolNotSupportedError):
        await method(agent)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_raises_invalid_prompt_input_error_with_none_prompt_and_none_input(
    llm_without_tool_call: MockLLM, method: Callable
):
    agent = Agent(llm=llm_without_tool_call, prompt=None)  # type: ignore

    with pytest.raises(AgentInvalidPromptInputError) as exc_info:
        await method(agent)

    assert exc_info.value.prompt_type is None
    assert exc_info.value.input_type is None
    assert "Invalid prompt/input combination: prompt=None, input=None" in str(exc_info.value)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_raises_invalid_prompt_input_error_with_invalid_types(llm_without_tool_call: MockLLM, method: Callable):
    agent = Agent(llm=llm_without_tool_call, prompt=123)  # type: ignore

    with pytest.raises(AgentInvalidPromptInputError) as exc_info:
        await method(agent, input={"key": "value"})

    assert exc_info.value.prompt_type == 123
    assert exc_info.value.input_type == {"key": "value"}
    assert "Invalid prompt/input combination" in str(exc_info.value)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_raises_invalid_prompt_input_error_with_list_input(llm_without_tool_call: MockLLM, method: Callable):
    agent = Agent(llm=llm_without_tool_call, prompt=None)  # type: ignore

    with pytest.raises(AgentInvalidPromptInputError) as exc_info:
        await method(agent, input=["item1", "item2"])

    assert exc_info.value.prompt_type is None
    assert exc_info.value.input_type == ["item1", "item2"]
    assert "Invalid prompt/input combination" in str(exc_info.value)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_with_initial_history(llm_without_tool_call: MockLLM, method: Callable):
    """Test agent with initial history."""
    initial_history = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="You are a weather assistant",
        history=initial_history,
        keep_history=True,
    )

    await method(agent, input="What's the weather like?")

    assert agent.history

    assert len(agent.history) == 5  # system + initial user + assistant + new user + new assistant
    assert agent.history[0]["role"] == "system"
    assert agent.history[0]["content"] == "You are a weather assistant"  #! Updated system prompt
    assert agent.history[1]["role"] == "user"
    assert agent.history[1]["content"] == "Hello"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] == "Hi there!"
    assert agent.history[3]["role"] == "user"
    assert agent.history[3]["content"] == "What's the weather like?"
    assert agent.history[4]["role"] == "assistant"
    assert agent.history[4]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_without_keep_history(llm_without_tool_call: MockLLM, method: Callable):
    """Test agent without history preservation."""
    initial_history = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"},
    ]

    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="System prompt",
        history=initial_history,
        keep_history=False,
    )

    result = await method(agent, input="New message")

    # Agent history should not be updated
    assert agent.history == initial_history
    # But result history should be updated
    assert len(result.history) == 5  # system + user + assistant + new user + new assistant
    assert result.history[0]["role"] == "system"
    assert result.history[0]["content"] == "System prompt"
    assert result.history[1]["role"] == "user"
    assert result.history[1]["content"] == "Previous message"
    assert result.history[2]["role"] == "assistant"
    assert result.history[2]["content"] == "Previous response"
    assert result.history[3]["role"] == "user"
    assert result.history[3]["content"] == "New message"
    assert result.history[4]["role"] == "assistant"
    assert result.history[4]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_string_prompt_and_input(llm_without_tool_call: MockLLM, method: Callable):
    """Test history handling with string prompt and string input."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="You are a helpful assistant",
        keep_history=True,
    )

    await method(agent, input="Hello")

    assert agent.history is not None
    assert len(agent.history) == 3  # system + user + assistant
    assert agent.history[0]["role"] == "system"
    assert agent.history[0]["content"] == "You are a helpful assistant"
    assert agent.history[1]["role"] == "user"
    assert agent.history[1]["content"] == "Hello"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_string_prompt_no_input(llm_without_tool_call: MockLLM, method: Callable):
    """Test history handling with string prompt and no input."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="Tell me a joke",
        keep_history=True,
    )

    await method(agent)

    assert agent.history is not None
    assert len(agent.history) == 2  # user (prompt) + assistant
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Tell me a joke"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_weather_prompt_with_history_multiple_runs(
    llm_without_tool_call: MockLLM, method: Callable
):
    """Test history handling with custom prompt class with input type."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt=WeatherPrompt,
        keep_history=True,
    )

    input_data = WeatherInput(location="London", date="today")
    await method(agent, input=input_data)

    input_data2 = WeatherInput(location="Paris", date="tomorrow")
    await method(agent, input=input_data2)

    assert agent.history is not None
    assert len(agent.history) == 5
    assert agent.history[0]["role"] == "system"
    assert agent.history[0]["content"] == "You are a weather assistant"
    assert agent.history[1]["role"] == "user"
    assert agent.history[1]["content"] == "What's the weather like in London on today?"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] == "Test LLM output"
    assert agent.history[3]["role"] == "user"
    assert agent.history[3]["content"] == "What's the weather like in Paris on tomorrow?"
    assert agent.history[4]["role"] == "assistant"
    assert agent.history[4]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_weather_prompt_no_history_multiple_runs(
    llm_without_tool_call: MockLLM, method: Callable
):
    """Test history handling with custom prompt class with input type."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt=WeatherPrompt,
        keep_history=False,
    )

    input_data = WeatherInput(location="London", date="today")
    result = await method(agent, input=input_data)
    assert agent.history == []
    assert result.history[0]["role"] == "system"
    assert result.history[0]["content"] == "You are a weather assistant"
    assert result.history[1]["role"] == "user"
    assert result.history[1]["content"] == "What's the weather like in London on today?"
    assert result.history[2]["role"] == "assistant"
    assert result.history[2]["content"] == "Test LLM output"

    input_data2 = WeatherInput(location="Paris", date="tomorrow")
    result2 = await method(agent, input=input_data2)
    assert agent.history == []
    assert result2.history[0]["role"] == "system"
    assert result2.history[0]["content"] == "You are a weather assistant"
    assert result2.history[1]["role"] == "user"
    assert result2.history[1]["content"] == "What's the weather like in Paris on tomorrow?"
    assert result2.history[2]["role"] == "assistant"
    assert result2.history[2]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_no_prompt_string_input(llm_without_tool_call: MockLLM, method: Callable):
    """Test history handling with no prompt and string input."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt=None,
        keep_history=True,
    )

    await method(agent, input="Direct message")

    assert agent.history is not None
    assert len(agent.history) == 2  # user + assistant
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Direct message"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_string_prompt_multiple_runs(llm_without_tool_call: MockLLM, method: Callable):
    """Test history accumulation across multiple runs."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="You are a helpful assistant",
        keep_history=True,
    )

    result1 = await method(agent, input="First message")
    assert result1.history is not None
    assert len(result1.history) == 3  # system + user + assistant

    result2 = await method(agent, input="Second message")
    assert result2.history is not None
    assert len(result2.history) == 5  # system + user1 + assistant1 + user2 + assistant2

    # Verify the conversation flow
    assert result2.history[0]["role"] == "system"
    assert result2.history[1]["role"] == "user"
    assert result2.history[1]["content"] == "First message"
    assert result2.history[2]["role"] == "assistant"
    assert result2.history[2]["content"] == "Test LLM output"
    assert result2.history[3]["role"] == "user"
    assert result2.history[3]["content"] == "Second message"
    assert result2.history[4]["role"] == "assistant"
    assert result2.history[4]["content"] == "Test LLM output"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_history_with_tools(llm_with_tool_call: MockLLM, method: Callable):
    """Test history handling with tool calls."""
    agent: Agent = Agent(
        llm=llm_with_tool_call,
        prompt="You are a weather assistant",
        tools=[get_weather],
        keep_history=True,
    )

    await method(agent, input="What's the weather in San Francisco?")

    assert len(agent.history) == 5

    assert agent.history[0]["role"] == "system"
    assert agent.history[1]["role"] == "user"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] is None  # Tool call message
    assert "tool_calls" in agent.history[2]
    assert agent.history[3]["role"] == "tool"
    assert agent.history[4]["role"] == "assistant"
    assert agent.history[4]["content"] == "Temperature is 72 fahrenheit"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_max_turns_exceeded(llm_with_tool_call: MockLLM, method: Callable):
    """Test that AgentMaxToolCallsExceededError is raised when max_tool_calls is exceeded in a single response."""
    agent = Agent(
        llm=llm_with_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
        default_options=AgentOptions(max_turns=1),
    )

    options: AgentOptions = AgentOptions(llm_options=None)

    with pytest.raises(AgentMaxTurnsExceededError) as exc_info:
        await method(agent, options=options)

    assert exc_info.value.max_turns == 1
    assert "The number of Agent turns exceeded the limit of 1" in str(exc_info.value)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_max_turns_not_exeeded_with_many_tool_calls(llm_multiple_tool_calls: MockLLM, method: Callable):
    """Test that AgentMaxToolCallsExceededError is raised when max_tool_calls is exceeded in a single response."""
    agent = Agent(
        llm=llm_multiple_tool_calls,
        prompt=CustomPrompt,
        tools=[get_weather],
        default_options=AgentOptions(max_turns=2),
    )

    options: AgentOptions = AgentOptions(llm_options=None)

    result = await method(agent, options=options)

    assert result.content == "Final response after multiple tool calls"
    assert len(result.tool_calls) == 3
