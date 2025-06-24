import json

import pytest
from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents._main import AgentResult, ToolCallResult
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
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


async def test_agent_with_initial_history(llm_without_tool_call: MockLLM):
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

    await agent.run("What's the weather like?")

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


async def test_agent_without_keep_history(llm_without_tool_call: MockLLM):
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

    result = await agent.run("New message")

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


async def test_agent_history_with_string_prompt_and_input(llm_without_tool_call: MockLLM):
    """Test history handling with string prompt and string input."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="You are a helpful assistant",
        keep_history=True,
    )

    await agent.run("Hello")

    assert agent.history is not None
    assert len(agent.history) == 3  # system + user + assistant
    assert agent.history[0]["role"] == "system"
    assert agent.history[0]["content"] == "You are a helpful assistant"
    assert agent.history[1]["role"] == "user"
    assert agent.history[1]["content"] == "Hello"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] == "Test LLM output"


async def test_agent_history_with_string_prompt_no_input(llm_without_tool_call: MockLLM):
    """Test history handling with string prompt and no input."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="Tell me a joke",
        keep_history=True,
    )

    await agent.run()

    assert agent.history is not None
    assert len(agent.history) == 2  # user (prompt) + assistant
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Tell me a joke"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Test LLM output"


async def test_agent_history_with_weather_prompt_with_history_multiple_runs(llm_without_tool_call: MockLLM):
    """Test history handling with custom prompt class with input type."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt=WeatherPrompt,
        keep_history=True,
    )

    input_data = WeatherInput(location="London", date="today")
    await agent.run(input_data)

    input_data2 = WeatherInput(location="Paris", date="tomorrow")
    await agent.run(input_data2)

    assert agent.history is not None
    print(agent.history)
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


async def test_agent_history_with_weather_prompt_no_history_multiple_runs(llm_without_tool_call: MockLLM):
    """Test history handling with custom prompt class with input type."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt=WeatherPrompt,
        keep_history=False,
    )

    input_data = WeatherInput(location="London", date="today")
    result = await agent.run(input_data)
    assert agent.history == []
    assert result.history[0]["role"] == "system"
    assert result.history[0]["content"] == "You are a weather assistant"
    assert result.history[1]["role"] == "user"
    assert result.history[1]["content"] == "What's the weather like in London on today?"
    assert result.history[2]["role"] == "assistant"
    assert result.history[2]["content"] == "Test LLM output"

    input_data2 = WeatherInput(location="Paris", date="tomorrow")
    result2 = await agent.run(input_data2)
    assert agent.history == []
    assert result2.history[0]["role"] == "system"
    assert result2.history[0]["content"] == "You are a weather assistant"
    assert result2.history[1]["role"] == "user"
    assert result2.history[1]["content"] == "What's the weather like in Paris on tomorrow?"
    assert result2.history[2]["role"] == "assistant"
    assert result2.history[2]["content"] == "Test LLM output"


async def test_agent_history_with_no_prompt_string_input(llm_without_tool_call: MockLLM):
    """Test history handling with no prompt and string input."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt=None,
        keep_history=True,
    )

    await agent.run("Direct message")

    assert agent.history is not None
    assert len(agent.history) == 2  # user + assistant
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Direct message"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Test LLM output"


async def test_agent_history_with_string_prompt_multiple_runs(llm_without_tool_call: MockLLM):
    """Test history accumulation across multiple runs."""
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="You are a helpful assistant",
        keep_history=True,
    )

    result1 = await agent.run("First message")
    assert result1.history is not None
    assert len(result1.history) == 3  # system + user + assistant

    result2 = await agent.run("Second message")
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


async def test_agent_history_with_tools(llm_with_tool_call: MockLLM):
    """Test history handling with tool calls."""
    agent: Agent = Agent(
        llm=llm_with_tool_call,
        prompt="You are a weather assistant",
        tools=[get_weather],
        keep_history=True,
    )

    await agent.run("What's the weather in San Francisco?")

    assert len(agent.history) == 5

    assert agent.history[0]["role"] == "system"
    assert agent.history[1]["role"] == "user"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] is None  # Tool call message
    assert "tool_calls" in agent.history[2]
    assert agent.history[3]["role"] == "tool"
    assert agent.history[4]["role"] == "assistant"
    assert agent.history[4]["content"] == "Temperature is 72 fahrenheit"
