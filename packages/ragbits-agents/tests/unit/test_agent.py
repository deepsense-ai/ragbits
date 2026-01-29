import json
from collections.abc import Callable
from typing import cast

import pytest
from pydantic import BaseModel

from ragbits.agents import Agent, AgentRunContext
from ragbits.agents._main import AgentOptions, AgentResult, AgentResultStreaming, ToolCallResult, ToolChoice
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
    AgentMaxTurnsExceededError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.agents.hooks import (
    EventType,
    Hook,
    PostToolHookCallback,
    PreToolHookCallback,
    PreToolInput,
    PreToolOutput,
)
from ragbits.core.llms.base import Usage, UsageItem
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


def get_weather_context(location: str, context: AgentRunContext | None) -> AgentRunContext | None:  # noqa: D417
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.

    Returns:
        The current weather for the given location.
    """
    return context


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


@pytest.fixture
def llm_with_tool_call_context() -> MockLLM:
    options = MockLLMOptions(
        response="Temperature is 72 fahrenheit",
        tool_calls=[
            {
                "name": "get_weather_context",
                "arguments": '{"location": "San Francisco"}',
                "id": "test",
                "type": "function",
            }
        ],
    )
    return MockLLM(default_options=options)


def get_time() -> str:
    """
    Returns the current time.

    Returns:
        The current time as a string.
    """
    return "12:00 PM"


@pytest.fixture
def llm_no_tool_call_when_none() -> MockLLM:
    """LLM that doesn't call tools when tool_choice is 'none'."""
    options = MockLLMOptions(response="I cannot call tools right now.")
    return MockLLM(default_options=options)


@pytest.fixture
def llm_auto_tool_call() -> MockLLM:
    """LLM that automatically decides to call a tool."""
    options = MockLLMOptions(
        response="Let me check the weather for you.",
        tool_calls=[
            {
                "name": "get_weather",
                "arguments": '{"location": "New York"}',
                "id": "auto_test",
                "type": "function",
            }
        ],
    )
    return MockLLM(default_options=options)


@pytest.fixture
def llm_required_tool_call() -> MockLLM:
    """LLM that is forced to call a tool when tool_choice is 'required'."""
    options = MockLLMOptions(
        response="",
        tool_calls=[
            {
                "name": "get_weather",
                "arguments": '{"location": "Boston"}',
                "id": "required_test",
                "type": "function",
            }
        ],
    )
    return MockLLM(default_options=options)


@pytest.fixture
def llm_specific_tool_call() -> MockLLM:
    """LLM that calls a specific tool when tool_choice is a specific function."""
    options = MockLLMOptions(
        response="",
        tool_calls=[
            {
                "name": "get_time",
                "arguments": "{}",
                "id": "specific_test",
                "type": "function",
            }
        ],
    )
    return MockLLM(default_options=options)


async def _run(
    agent: Agent,
    input: str | BaseModel | None = None,
    options: AgentOptions | None = None,
    context: AgentRunContext | None = None,
    tool_choice: ToolChoice | None = None,
) -> AgentResult:
    return await agent.run(input, options=options, context=context, tool_choice=tool_choice)


async def _run_streaming(
    agent: Agent,
    input: str | BaseModel | None = None,
    options: AgentOptions | None = None,
    context: AgentRunContext | None = None,
    tool_choice: ToolChoice | None = None,
) -> AgentResultStreaming:
    result = agent.run_streaming(input, options=options, context=context, tool_choice=tool_choice)
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
            result='{"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"}',
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


@pytest.mark.parametrize(
    ("method", "context"),
    [(_run, None), (_run, AgentRunContext()), (_run_streaming, None), (_run_streaming, AgentRunContext())],
)
async def test_agent_run_tools_with_context(
    llm_with_tool_call_context: MockLLM, method: Callable, context: AgentRunContext | None
):
    agent = Agent(
        llm=llm_with_tool_call_context,
        prompt=CustomPrompt,
        tools=[get_weather_context],
    )

    result = await method(agent, context=context)

    assert result.content == "Temperature is 72 fahrenheit"
    assert result.tool_calls[0].id == "test"
    assert result.tool_calls[0].name == "get_weather_context"
    assert result.tool_calls[0].arguments == {"location": "San Francisco"}
    assert isinstance(result.tool_calls[0].result, AgentRunContext)


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_run_context_is_updated(llm_without_tool_call: MockLLM, method: Callable):
    context: AgentRunContext = AgentRunContext()
    agent: Agent = Agent(
        llm=llm_without_tool_call,
        prompt="NOT IMPORTANT",
    )
    _ = await method(agent, context=context)
    assert context.usage == Usage(
        requests=[
            UsageItem(
                model="mock:mock",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                estimated_cost=0.0,
            )
        ]
    )


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


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_run_with_tool_choice_none(llm_no_tool_call_when_none: MockLLM, method: Callable):
    """Test agent run with tool_choice set to 'none'."""
    agent = Agent(
        llm=llm_no_tool_call_when_none,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await method(agent, tool_choice="none")

    assert result.content == "I cannot call tools right now."
    assert result.tool_calls is None


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_run_with_auto_tool_call(llm_auto_tool_call: MockLLM, method: Callable):
    """Test agent run with automatic tool call."""
    agent = Agent(
        llm=llm_auto_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await method(agent)

    assert result.content == "Let me check the weather for you."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "auto_test"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_run_with_required_tool_call(llm_required_tool_call: MockLLM, method: Callable):
    """Test agent run with required tool call."""
    agent = Agent(
        llm=llm_required_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await method(agent, tool_choice="required")

    assert result.content == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "required_test"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_run_with_specific_tool_call(llm_specific_tool_call: MockLLM, method: Callable):
    """Test agent run with specific tool call."""
    agent = Agent(
        llm=llm_specific_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather, get_time],
    )
    result = await method(agent, tool_choice=get_time)

    assert result.content == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "specific_test"
    assert result.tool_calls[0].name == "get_time"
    assert result.tool_calls[0].result == "12:00 PM"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_agent_run_with_tool_choice_auto_explicit(llm_auto_tool_call: MockLLM, method: Callable):
    """Test agent run with tool_choice explicitly set to 'auto'."""
    agent = Agent(
        llm=llm_auto_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather],
    )
    result = await method(agent, tool_choice="auto")

    assert result.content == "Let me check the weather for you."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_weather"
    assert result.tool_calls[0].arguments == {"location": "New York"}


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_tool_choice_with_multiple_tools_available(llm_auto_tool_call: MockLLM, method: Callable):
    """Test tool_choice behavior when multiple tools are available."""
    agent = Agent(
        llm=llm_auto_tool_call,
        prompt=CustomPrompt,
        tools=[get_weather, get_time],  # Multiple tools available
    )

    result = await method(agent, tool_choice="auto")

    assert result.content == "Let me check the weather for you."
    assert len(result.tool_calls) == 1
    # The LLM chose to call get_weather based on its configuration
    assert result.tool_calls[0].name == "get_weather"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_tool_choice_history_preservation(llm_with_tool_call: MockLLM, method: Callable):
    """Test that tool_choice works correctly with history preservation."""
    agent: Agent = Agent(
        llm=llm_with_tool_call,
        prompt="You are a helpful assistant",
        tools=[get_weather],
        keep_history=True,
    )

    await method(agent, input="Check weather", tool_choice="auto")
    assert len(agent.history) >= 3  # At least system, user, assistant messages
    # Should include tool call in history
    tool_call_messages = [msg for msg in agent.history if msg.get("role") == "tool"]
    assert len(tool_call_messages) >= 1


async def test_explicit_input_type_prompt_creation():
    class CustomInput(BaseModel):
        foo: int
        bar: str

    @Agent.prompt_config(CustomInput)
    class AgentWithExplicitInput(Agent):
        system_prompt = "System prompt"
        user_prompt = "{{ foo }} {{ bar }}"

    prompt_cls = AgentWithExplicitInput.prompt_cls
    assert prompt_cls is not None
    assert issubclass(prompt_cls, Prompt)
    assert prompt_cls.system_prompt == "System prompt"
    assert prompt_cls.user_prompt == "{{ foo }} {{ bar }}"


async def test_default_user_prompt_is_input_placeholder():
    class CustomInputModel(BaseModel):
        input: int

    @Agent.prompt_config(CustomInputModel)
    class AgentExplicitPrompt(Agent):
        system_prompt = "Explicit system"

    prompt_cls2 = AgentExplicitPrompt.prompt_cls
    assert prompt_cls2 is not None
    assert issubclass(prompt_cls2, Prompt)
    assert prompt_cls2.user_prompt == "{{ input }}"


async def test_input_type_check_with_system_prompt(llm_with_tool_call: MockLLM):
    class AgentExplicitPrompt(Agent):
        system_prompt = "Explicit system"

    with pytest.raises(ValueError):
        AgentExplicitPrompt(
            llm=llm_with_tool_call,
            prompt="You are a helpful assistant",
            tools=[get_weather],
            keep_history=True,
        )


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_pre_tool_hook_denies_execution(
    llm_with_tool_call: MockLLM, method: Callable, deny_hook: PreToolHookCallback
):
    """Test that a pre-tool hook can deny tool execution."""
    hook = Hook(event_type=EventType.PRE_TOOL, callback=deny_hook)
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=[hook])

    result = await method(agent)

    assert result.tool_calls[0].result == "Blocked by hook"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_pre_tool_hook_denies_only_matching_tool(
    llm_with_tool_call: MockLLM, method: Callable, deny_hook: PreToolHookCallback
):
    """Test that a hook with tools filter only affects matching tools."""
    hook = Hook(event_type=EventType.PRE_TOOL, callback=deny_hook, tool_names=["other_tool"])
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=[hook])

    result = await method(agent)

    # Tool should execute normally since hook doesn't match
    assert "72" in result.tool_calls[0].result


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_pre_tool_hook_modifies_arguments(
    llm_with_tool_call: MockLLM, method: Callable, add_field: Callable[..., PreToolHookCallback]
):
    """Test that a pre-tool hook can modify tool arguments."""
    hook = Hook(event_type=EventType.PRE_TOOL, callback=add_field("location", "New York"))
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=[hook])

    result = await method(agent)

    assert result.tool_calls[0].arguments["location"] == "New York"


@pytest.mark.parametrize("method", [_run, _run_streaming])
async def test_post_tool_hook_modifies_output(
    llm_with_tool_call: MockLLM, method: Callable, append_output: Callable[..., PostToolHookCallback]
):
    """Test that a post-tool hook can modify tool output."""
    hook = Hook(event_type=EventType.POST_TOOL, callback=append_output("[MODIFIED]", prepend=True))
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=[hook])

    result = await method(agent)

    assert result.tool_calls[0].result.startswith("[MODIFIED]")


async def test_pre_tool_hook_ask_yields_confirmation_request(
    llm_with_tool_call: MockLLM, ask_hook: PreToolHookCallback
):
    """Test that ask decision yields a ConfirmationRequest."""
    hook = Hook(event_type=EventType.PRE_TOOL, callback=ask_hook)
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=[hook])

    events = []
    async for event in agent.run_streaming():
        events.append(event)

    confirmation_requests = [e for e in events if isinstance(e, ConfirmationRequest)]
    assert len(confirmation_requests) == 1
    assert confirmation_requests[0].tool_name == "get_weather"


async def test_pre_tool_hook_ask_with_confirmation_approved(llm_with_tool_call: MockLLM, ask_hook: PreToolHookCallback):
    """Test that approved confirmation allows tool execution."""
    hook = Hook(event_type=EventType.PRE_TOOL, callback=ask_hook)
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=[hook])

    # First run to get confirmation_id
    events = []
    async for event in agent.run_streaming():
        events.append(event)
    confirmation_request = next(e for e in events if isinstance(e, ConfirmationRequest))

    # Second run with confirmation approved
    context: AgentRunContext = AgentRunContext(
        tool_confirmations=[{"confirmation_id": confirmation_request.confirmation_id, "confirmed": True}]
    )
    result = await agent.run(context=context)

    assert result.tool_calls is not None
    assert "72" in result.tool_calls[0].result


async def test_hook_priority_order(llm_with_tool_call: MockLLM):
    """Test that hooks execute in priority order (lower first)."""
    execution_order: list[int] = []

    async def hook_priority_10(input_data: PreToolInput) -> PreToolOutput:
        execution_order.append(10)
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    async def hook_priority_5(input_data: PreToolInput) -> PreToolOutput:
        execution_order.append(5)
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    hooks = [
        Hook(event_type=EventType.PRE_TOOL, callback=hook_priority_10, priority=10),
        Hook(event_type=EventType.PRE_TOOL, callback=hook_priority_5, priority=5),
    ]
    agent = Agent(llm=llm_with_tool_call, prompt=CustomPrompt, tools=[get_weather], hooks=hooks)

    await agent.run()

    assert execution_order == [5, 10]
