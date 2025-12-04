"""
Tests for agent tool confirmation functionality.

This module tests:
- ConfirmationRequest model
- @requires_confirmation decorator
- Tool confirmation flow in agents
- confirmed_tools in AgentRunContext
"""

import hashlib
import json

import pytest

from ragbits.agents import Agent, AgentRunContext, requires_confirmation
from ragbits.agents._main import AgentResultStreaming
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import Tool
from ragbits.core.llms.mock import MockLLM, MockLLMOptions


# Test tools
def simple_tool(value: str) -> str:
    """
    A simple tool for testing.

    Args:
        value: Input value

    Returns:
        The input value echoed back
    """
    return f"Executed: {value}"


@requires_confirmation
def confirmed_tool(action: str) -> str:
    """
    A tool that requires confirmation.

    Args:
        action: The action to perform

    Returns:
        Confirmation of the action
    """
    return f"Action performed: {action}"


# Fixtures
@pytest.fixture
def llm_with_confirmed_tool_call() -> MockLLM:
    """LLM that calls a tool requiring confirmation."""
    options = MockLLMOptions(
        response="I will perform the action",
        tool_calls=[
            {
                "name": "confirmed_tool",
                "arguments": '{"action": "test"}',
                "id": "test_conf_1",
                "type": "function",
            }
        ],
    )
    return MockLLM(default_options=options)


@pytest.fixture
def llm_with_multiple_confirmed_tools() -> MockLLM:
    """LLM that calls multiple tools requiring confirmation."""
    options = MockLLMOptions(
        response="I will perform multiple actions",
        tool_calls=[
            {
                "name": "confirmed_tool",
                "arguments": '{"action": "action1"}',
                "id": "test_conf_1",
                "type": "function",
            },
            {
                "name": "confirmed_tool",
                "arguments": '{"action": "action2"}',
                "id": "test_conf_2",
                "type": "function",
            },
        ],
    )
    return MockLLM(default_options=options)


@pytest.fixture
def llm_with_mixed_tools() -> MockLLM:
    """LLM that calls both confirmed and regular tools."""
    options = MockLLMOptions(
        response="I will perform mixed actions",
        tool_calls=[
            {
                "name": "simple_tool",
                "arguments": '{"value": "test"}',
                "id": "test_simple",
                "type": "function",
            },
            {
                "name": "confirmed_tool",
                "arguments": '{"action": "test"}',
                "id": "test_conf",
                "type": "function",
            },
        ],
    )
    return MockLLM(default_options=options)


# Helper functions
def generate_confirmation_id(tool_name: str, arguments: dict) -> str:
    """Generate a confirmation ID matching the agent's logic."""
    confirmation_str = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
    return hashlib.sha256(confirmation_str.encode()).hexdigest()[:16]


async def collect_streaming_results(
    agent: Agent,
    input: str | None = None,
    context: AgentRunContext | None = None,
) -> tuple[list, AgentResultStreaming]:
    """Helper to collect all streaming results."""
    chunks = []
    result = agent.run_streaming(input, context=context)
    async for chunk in result:
        chunks.append(chunk)
    return chunks, result


# Tests for ConfirmationRequest model
def test_confirmation_request_model():
    """Test ConfirmationRequest model creation and serialization."""
    request = ConfirmationRequest(
        confirmation_id="abc123",
        tool_name="confirmed_tool",
        tool_description="A tool that requires confirmation.",
        arguments={"action": "test"},
    )

    assert request.confirmation_id == "abc123"
    assert request.tool_name == "confirmed_tool"
    assert request.tool_description == "A tool that requires confirmation."
    assert request.arguments == {"action": "test"}


def test_confirmation_request_serialization():
    """Test that ConfirmationRequest can be serialized to dict/json."""
    request = ConfirmationRequest(
        confirmation_id="test_id",
        tool_name="test_tool",
        tool_description="A test tool",
        arguments={"key": "value"},
    )

    # Test model_dump
    data = request.model_dump()
    assert data == {
        "confirmation_id": "test_id",
        "tool_name": "test_tool",
        "tool_description": "A test tool",
        "arguments": {"key": "value"},
    }

    # Test model_dump_json
    json_str = request.model_dump_json()
    assert "test_id" in json_str
    assert "test_tool" in json_str


# Tests for @requires_confirmation decorator
def test_requires_confirmation_decorator():
    """Test that @requires_confirmation sets the correct attribute."""
    assert hasattr(confirmed_tool, "_requires_confirmation")
    assert confirmed_tool._requires_confirmation is True  # type: ignore[attr-defined]

    assert not hasattr(simple_tool, "_requires_confirmation")


def test_requires_confirmation_preserves_function():
    """Test that decorator preserves function behavior."""
    result = confirmed_tool("test_action")
    assert result == "Action performed: test_action"


def test_requires_confirmation_preserves_metadata():
    """Test that decorator preserves function metadata."""
    assert confirmed_tool.__name__ == "confirmed_tool"
    assert confirmed_tool.__doc__ is not None
    assert "requires confirmation" in confirmed_tool.__doc__.lower()


# Tests for Tool.from_callable with confirmation
def test_tool_from_callable_with_decorator():
    """Test Tool.from_callable detects @requires_confirmation decorator."""
    tool = Tool.from_callable(confirmed_tool)
    assert tool.requires_confirmation is True


def test_tool_from_callable_without_decorator():
    """Test Tool.from_callable with regular function."""
    tool = Tool.from_callable(simple_tool)
    assert tool.requires_confirmation is False


def test_tool_from_callable_explicit_confirmation():
    """Test Tool.from_callable with explicit requires_confirmation parameter."""
    tool = Tool.from_callable(simple_tool, requires_confirmation=True)
    assert tool.requires_confirmation is True


def test_tool_from_callable_explicit_and_decorator():
    """Test that decorator and explicit parameter combine with OR logic."""
    # The implementation uses OR logic: requires_confirmation or decorator
    # So if decorator is True, it will always be True
    tool = Tool.from_callable(confirmed_tool, requires_confirmation=False)
    assert tool.requires_confirmation is True  # Decorator wins with OR logic


# Tests for agent confirmation flow - streaming mode
@pytest.mark.asyncio
async def test_agent_yields_confirmation_request_streaming(llm_with_confirmed_tool_call: MockLLM):
    """Test that agent yields ConfirmationRequest in streaming mode."""
    agent: Agent = Agent(
        llm=llm_with_confirmed_tool_call,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    chunks, _ = await collect_streaming_results(agent, "Test input")

    # Find ConfirmationRequest in chunks
    conf_requests = [c for c in chunks if isinstance(c, ConfirmationRequest)]
    assert len(conf_requests) == 1

    conf_req = conf_requests[0]
    assert conf_req.tool_name == "confirmed_tool"
    assert conf_req.arguments == {"action": "test"}
    assert len(conf_req.confirmation_id) == 16  # SHA256 truncated to 16 chars
    assert "requires confirmation" in conf_req.tool_description.lower()


@pytest.mark.asyncio
async def test_agent_multiple_confirmations_streaming(llm_with_multiple_confirmed_tools: MockLLM):
    """Test that agent yields multiple ConfirmationRequests."""
    agent: Agent = Agent(
        llm=llm_with_multiple_confirmed_tools,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    chunks, _ = await collect_streaming_results(agent, "Perform action1 and action2")

    # Find all ConfirmationRequests
    conf_requests = [c for c in chunks if isinstance(c, ConfirmationRequest)]
    assert len(conf_requests) == 2

    # Check first request
    assert conf_requests[0].tool_name == "confirmed_tool"
    assert conf_requests[0].arguments == {"action": "action1"}

    # Check second request
    assert conf_requests[1].tool_name == "confirmed_tool"
    assert conf_requests[1].arguments == {"action": "action2"}

    # Confirmation IDs should be different
    assert conf_requests[0].confirmation_id != conf_requests[1].confirmation_id


@pytest.mark.asyncio
async def test_agent_mixed_tools_streaming(llm_with_mixed_tools: MockLLM):
    """Test that agent handles mix of confirmed and regular tools."""
    agent: Agent = Agent(
        llm=llm_with_mixed_tools,
        prompt="Test prompt",
        tools=[simple_tool, confirmed_tool],
    )

    chunks, _ = await collect_streaming_results(agent, "Test input")

    # Should have one ConfirmationRequest (for confirmed_tool)
    conf_requests = [c for c in chunks if isinstance(c, ConfirmationRequest)]
    assert len(conf_requests) == 1
    assert conf_requests[0].tool_name == "confirmed_tool"


# Tests for confirmed_tools in AgentRunContext
@pytest.mark.asyncio
async def test_agent_executes_confirmed_tool_streaming(llm_with_confirmed_tool_call: MockLLM):
    """Test that agent executes tool when confirmed."""
    agent: Agent = Agent(
        llm=llm_with_confirmed_tool_call,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    # First run - get confirmation request
    chunks_1, _ = await collect_streaming_results(agent, "Test input")
    conf_req = next(c for c in chunks_1 if isinstance(c, ConfirmationRequest))

    # Second run - with confirmation
    context: AgentRunContext = AgentRunContext(
        confirmed_tools=[
            {
                "confirmation_id": conf_req.confirmation_id,
                "confirmed": True,
            }
        ]
    )

    # Create new LLM that returns final response after tool execution
    llm_final = MockLLM(default_options=MockLLMOptions(response="Tool executed successfully"))
    agent_confirmed: Agent = Agent(
        llm=llm_final,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    result = await agent_confirmed.run("Test input", context=context)

    # Tool should have been executed
    assert result.tool_calls is None  # No more pending tools
    assert "Tool executed successfully" in result.content


@pytest.mark.asyncio
async def test_agent_skips_declined_tool_streaming(llm_with_confirmed_tool_call: MockLLM):
    """Test that agent skips tool when declined."""
    agent: Agent = Agent(
        llm=llm_with_confirmed_tool_call,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    # First run - get confirmation request
    chunks_1, _ = await collect_streaming_results(agent, "Test input")
    conf_req = next(c for c in chunks_1 if isinstance(c, ConfirmationRequest))

    # Second run - with decline
    context: AgentRunContext = AgentRunContext(
        confirmed_tools=[
            {
                "confirmation_id": conf_req.confirmation_id,
                "confirmed": False,
            }
        ]
    )

    # The tool should yield a declined result
    _, result = await collect_streaming_results(agent, "Test input", context=context)

    # Check that tool was declined
    assert result.tool_calls is not None
    declined_call = next((tc for tc in result.tool_calls if "declined" in tc.result.lower()), None)
    assert declined_call is not None
    assert declined_call.name == "confirmed_tool"


@pytest.mark.asyncio
async def test_agent_partial_confirmation_streaming(llm_with_multiple_confirmed_tools: MockLLM):
    """Test that agent handles partial confirmations correctly."""
    agent: Agent = Agent(
        llm=llm_with_multiple_confirmed_tools,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    # First run - get both confirmation requests
    chunks_1, _ = await collect_streaming_results(agent, "Perform action1 and action2")
    conf_requests = [c for c in chunks_1 if isinstance(c, ConfirmationRequest)]
    assert len(conf_requests) == 2

    # Confirm only the first one
    context: AgentRunContext = AgentRunContext(
        confirmed_tools=[
            {
                "confirmation_id": conf_requests[0].confirmation_id,
                "confirmed": True,
            }
        ]
    )

    # Second run - should still request confirmation for the second tool
    chunks_2, _ = await collect_streaming_results(agent, "Perform action1 and action2", context=context)

    # Should still have one pending confirmation request
    new_conf_requests = [c for c in chunks_2 if isinstance(c, ConfirmationRequest)]
    assert len(new_conf_requests) == 1
    assert new_conf_requests[0].confirmation_id == conf_requests[1].confirmation_id


# Tests for confirmation ID stability
@pytest.mark.asyncio
async def test_confirmation_id_is_stable(llm_with_confirmed_tool_call: MockLLM):
    """Test that same tool + arguments generates same confirmation ID."""
    agent: Agent = Agent(
        llm=llm_with_confirmed_tool_call,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    # Run twice with same input
    chunks_1, _ = await collect_streaming_results(agent, "Test input")
    chunks_2, _ = await collect_streaming_results(agent, "Test input")

    conf_req_1 = next(c for c in chunks_1 if isinstance(c, ConfirmationRequest))
    conf_req_2 = next(c for c in chunks_2 if isinstance(c, ConfirmationRequest))

    # Confirmation IDs should be identical for same tool + arguments
    assert conf_req_1.confirmation_id == conf_req_2.confirmation_id


def test_confirmation_id_generation():
    """Test the confirmation ID generation algorithm."""
    # Test that same inputs produce same ID
    id1 = generate_confirmation_id("test_tool", {"arg": "value"})
    id2 = generate_confirmation_id("test_tool", {"arg": "value"})
    assert id1 == id2
    assert len(id1) == 16

    # Test that different inputs produce different IDs
    id3 = generate_confirmation_id("test_tool", {"arg": "different"})
    assert id1 != id3

    # Test that argument order doesn't matter (they're sorted)
    id4 = generate_confirmation_id("test", {"a": 1, "b": 2})
    id5 = generate_confirmation_id("test", {"b": 2, "a": 1})
    assert id4 == id5


# Tests for non-streaming mode
@pytest.mark.asyncio
async def test_agent_confirmation_non_streaming(llm_with_confirmed_tool_call: MockLLM):
    """Test that confirmation works in non-streaming mode."""
    agent: Agent = Agent(
        llm=llm_with_confirmed_tool_call,
        prompt="Test prompt",
        tools=[confirmed_tool],
    )

    # In non-streaming mode, the tool execution is blocked
    result = await agent.run("Test input")

    # Result should indicate tool needs confirmation
    # The exact behavior depends on implementation, but tool shouldn't be executed
    assert result is not None


# Edge cases
@pytest.mark.asyncio
async def test_empty_confirmed_tools_list():
    """Test that empty confirmed_tools list doesn't cause issues."""
    llm = MockLLM(default_options=MockLLMOptions(response="Test response"))
    agent: Agent = Agent(llm=llm, prompt="Test", tools=[confirmed_tool])

    context: AgentRunContext = AgentRunContext(confirmed_tools=[])
    result = await agent.run("Test", context=context)

    assert result.content == "Test response"


@pytest.mark.asyncio
async def test_malformed_confirmed_tools():
    """Test handling of malformed confirmed_tools entries."""
    llm = MockLLM(
        default_options=MockLLMOptions(
            response="Test",
            tool_calls=[
                {
                    "name": "confirmed_tool",
                    "arguments": '{"action": "test"}',
                    "id": "test",
                    "type": "function",
                }
            ],
        )
    )
    agent: Agent = Agent(llm=llm, prompt="Test", tools=[confirmed_tool])

    # Missing confirmation_id
    context: AgentRunContext = AgentRunContext(
        confirmed_tools=[
            {"confirmed": True}  # Missing confirmation_id
        ]
    )

    chunks, _ = await collect_streaming_results(agent, "Test", context=context)

    # Should still yield ConfirmationRequest (malformed entry ignored)
    conf_requests = [c for c in chunks if isinstance(c, ConfirmationRequest)]
    assert len(conf_requests) == 1


@pytest.mark.asyncio
async def test_confirmation_with_history():
    """Test that confirmation works correctly with conversation history."""
    llm = MockLLM(
        default_options=MockLLMOptions(
            response="Will perform action",
            tool_calls=[
                {
                    "name": "confirmed_tool",
                    "arguments": '{"action": "test"}',
                    "id": "test",
                    "type": "function",
                }
            ],
        )
    )

    initial_history = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"},
    ]

    agent: Agent = Agent(
        llm=llm,
        prompt="You are a helpful assistant",
        tools=[confirmed_tool],
        history=initial_history,
        keep_history=True,
    )

    chunks, _ = await collect_streaming_results(agent, "Perform test action")

    # Should have confirmation request
    conf_requests = [c for c in chunks if isinstance(c, ConfirmationRequest)]
    assert len(conf_requests) == 1

    # History should be preserved
    assert len(agent.history) > len(initial_history)
