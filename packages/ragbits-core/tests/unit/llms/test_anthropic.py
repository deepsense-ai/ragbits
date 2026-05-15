"""
Tests for AnthropicLLM.

Because the 'anthropic' package is an optional dependency, every test that
instantiates AnthropicLLM must patch HAS_ANTHROPIC=True and stub out the
AsyncAnthropic constructor so the missing SDK is never invoked.
"""

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.core.llms.anthropic import AnthropicLLM, AnthropicLLMOptions
from ragbits.core.llms.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMStatusError,
)
from ragbits.core.prompt.base import BasePrompt, ChatFormat

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockPrompt(BasePrompt):
    def __init__(self, message: str, system: str | None = None):
        self.message = message
        self._system = system

    @property
    def chat(self) -> ChatFormat:
        messages: ChatFormat = []
        if self._system:
            messages.append({"role": "system", "content": self._system})
        messages.append({"role": "user", "content": self.message})
        return messages


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_thinking_block(thinking: str) -> MagicMock:
    block = MagicMock()
    block.type = "thinking"
    block.thinking = thinking
    return block


def _make_tool_use_block(name: str, input_data: dict[str, Any], id: str = "toolu_123") -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_data
    block.id = id
    return block


def _make_anthropic_response(blocks: list, input_tokens: int = 10, output_tokens: int = 20) -> MagicMock:
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = blocks
    response.usage = usage
    return response


def get_weather(location: str) -> str:
    """Returns the current weather for a given location."""
    return json.dumps({"location": location, "temperature": "72"})


def _make_llm() -> AnthropicLLM:
    """Create an AnthropicLLM with a stub client (no real anthropic SDK needed)."""
    mock_client = MagicMock()
    with (
        patch("ragbits.core.llms.anthropic.HAS_ANTHROPIC", True),
        patch("ragbits.core.llms.anthropic.AsyncAnthropic", return_value=mock_client, create=True),
    ):
        llm = AnthropicLLM(api_key="test-key")
    # client is already set; tests can overwrite llm._client.messages.create directly
    return llm


# ---------------------------------------------------------------------------
# Basic generation
# ---------------------------------------------------------------------------


async def test_generation():
    """Basic text generation."""
    llm = _make_llm()
    llm._client.messages.create = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_anthropic_response([_make_text_block("I'm fine, thank you.")])
    )

    result = await llm.generate(MockPrompt("Hello, how are you?"))

    assert result == "I'm fine, thank you."


async def test_generation_with_metadata():
    """generate_with_metadata returns content and token usage."""
    llm = _make_llm()
    llm._client.messages.create = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_anthropic_response(
            [_make_text_block("Great!")],
            input_tokens=5,
            output_tokens=15,
        )
    )

    output = await llm.generate_with_metadata(MockPrompt("Hello!"))

    assert output.content == "Great!"
    assert output.usage is not None
    assert output.usage.prompt_tokens == 5
    assert output.usage.completion_tokens == 15
    assert output.usage.total_tokens == 20


async def test_generation_with_reasoning():
    """Thinking blocks are surfaced as reasoning in generate_with_metadata."""
    llm = _make_llm()
    llm._client.messages.create = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_anthropic_response(
            [_make_thinking_block("Let me think..."), _make_text_block("The answer is 42.")]
        )
    )

    output = await llm.generate_with_metadata(MockPrompt("What is 6x7?"))

    assert output.content == "The answer is 42."
    assert output.reasoning == "Let me think..."


async def test_generation_with_tools():
    """Tool calls are returned when the model calls a tool."""
    llm = _make_llm()
    llm._client.messages.create = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_anthropic_response(
            [_make_tool_use_block("get_weather", {"location": "San Francisco"}, "toolu_abc")]
        )
    )

    result = await llm.generate(MockPrompt("Weather?"), tools=[get_weather])

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "get_weather"
    assert result[0].id == "toolu_abc"
    assert result[0].type == "function"
    assert result[0].arguments == {"location": "San Francisco"}


async def test_generation_with_tools_no_tool_used():
    """Plain text returned when tools provided but not called."""
    llm = _make_llm()
    llm._client.messages.create = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_anthropic_response([_make_text_block("I don't need tools.")])
    )

    result = await llm.generate(MockPrompt("Hello!"), tools=[get_weather])

    assert isinstance(result, str)
    assert result == "I don't need tools."


async def test_empty_response_raises():
    """Empty content list raises LLMEmptyResponseError."""
    llm = _make_llm()
    llm._client.messages.create = AsyncMock(return_value=_make_anthropic_response([]))  # type: ignore[method-assign]

    with pytest.raises(LLMEmptyResponseError):
        await llm.generate(MockPrompt("Hello!"))


def test_get_model_id():
    llm = _make_llm()
    llm.model_name = "claude-opus-4-6"
    assert llm.get_model_id() == "anthropic:claude-opus-4-6"


def test_common_options_are_sent_to_anthropic_api():
    llm = _make_llm()
    kwargs = llm._build_create_kwargs(
        conversation=[{"role": "user", "content": "Hello!"}],
        system=None,
        options=AnthropicLLMOptions(max_tokens=100, temperature=0.5, top_p=0.8),
        tools=None,
        tool_choice=None,
    )

    assert kwargs["max_tokens"] == 100
    assert kwargs["temperature"] == 0.5
    assert kwargs["top_p"] == 0.8


# ---------------------------------------------------------------------------
# _convert_messages tests (static — no SDK needed)
# ---------------------------------------------------------------------------


def test_convert_messages_extracts_system():
    """System messages are extracted and returned separately."""
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
    ]
    system, converted = AnthropicLLM._convert_messages(messages)
    assert system == "You are helpful."
    assert converted == [{"role": "user", "content": "Hello!"}]


def test_convert_messages_no_system():
    messages = [{"role": "user", "content": "Hello!"}]
    system, converted = AnthropicLLM._convert_messages(messages)
    assert system is None
    assert converted == [{"role": "user", "content": "Hello!"}]


def test_convert_messages_multiple_system_parts():
    """Multiple system messages are joined with double newline."""
    messages = [
        {"role": "system", "content": "Part one."},
        {"role": "system", "content": "Part two."},
        {"role": "user", "content": "Hi"},
    ]
    system, _ = AnthropicLLM._convert_messages(messages)
    assert system == "Part one.\n\nPart two."


def test_convert_messages_tool_calls():
    """Assistant tool_calls are converted to tool_use content blocks."""
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {"name": "get_weather", "arguments": '{"location":"NYC"}'},
                }
            ],
        }
    ]
    _, converted = AnthropicLLM._convert_messages(messages)
    assert len(converted) == 1
    assert converted[0]["role"] == "assistant"
    parts = converted[0]["content"]
    assert parts[0] == {
        "type": "tool_use",
        "id": "call_1",
        "name": "get_weather",
        "input": {"location": "NYC"},
    }


def test_convert_messages_tool_results_grouped():
    """Consecutive tool messages are grouped into a single user message."""
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "function": {"name": "fn_a", "arguments": "{}"}},
                {"id": "call_2", "function": {"name": "fn_b", "arguments": "{}"}},
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "result_a"},
        {"role": "tool", "tool_call_id": "call_2", "content": "result_b"},
    ]
    _, converted = AnthropicLLM._convert_messages(messages)
    # Should have: 1 assistant message + 1 user message containing both tool results
    assert len(converted) == 2
    user_msg = converted[1]
    assert user_msg["role"] == "user"
    results = user_msg["content"]
    assert len(results) == 2
    assert results[0] == {"type": "tool_result", "tool_use_id": "call_1", "content": "result_a"}
    assert results[1] == {"type": "tool_result", "tool_use_id": "call_2", "content": "result_b"}


def test_convert_tools():
    """Tool definitions are converted to Anthropic format."""
    openai_tools = [
        {
            "function": {
                "name": "get_weather",
                "description": "Get the weather",
                "parameters": {"type": "object", "properties": {"location": {"type": "string"}}},
            }
        }
    ]
    result = AnthropicLLM._convert_tools(openai_tools)
    assert result == [
        {
            "name": "get_weather",
            "description": "Get the weather",
            "input_schema": {"type": "object", "properties": {"location": {"type": "string"}}},
        }
    ]


# ---------------------------------------------------------------------------
# Error handling — need to patch the anthropic module reference in the LLM
# ---------------------------------------------------------------------------


async def test_api_connection_error():
    """APIConnectionError is wrapped as LLMConnectionError."""

    class FakeBaseError(Exception):
        pass

    class FakeConnectionError(FakeBaseError):
        pass

    class FakeStatusError(FakeBaseError):
        def __init__(
            self, message: str, status_code: int = 500, response: object | None = None, body: object | None = None
        ):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    class FakeValidationError(FakeBaseError):
        pass

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.APIConnectionError = FakeConnectionError
    mock_anthropic_module.APIStatusError = FakeStatusError
    mock_anthropic_module.APIResponseValidationError = FakeValidationError

    llm = _make_llm()
    llm._client.messages.create = AsyncMock(side_effect=FakeConnectionError("timeout"))  # type: ignore[method-assign]

    with (
        patch("ragbits.core.llms.anthropic.anthropic", mock_anthropic_module, create=True),
        pytest.raises(LLMConnectionError),
    ):
        await llm.generate(MockPrompt("Hello!"))


async def test_api_status_error():
    """APIStatusError is wrapped as LLMStatusError."""

    class FakeBaseError(Exception):
        pass

    class FakeConnectionError(FakeBaseError):
        pass

    class FakeStatusError(FakeBaseError):
        def __init__(
            self, message: str, status_code: int = 500, response: object | None = None, body: object | None = None
        ):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    class FakeValidationError(FakeBaseError):
        pass

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.APIConnectionError = FakeConnectionError
    mock_anthropic_module.APIStatusError = FakeStatusError
    mock_anthropic_module.APIResponseValidationError = FakeValidationError

    llm = _make_llm()
    llm._client.messages.create = AsyncMock(side_effect=FakeStatusError("forbidden", status_code=403))  # type: ignore[method-assign]

    with (
        patch("ragbits.core.llms.anthropic.anthropic", mock_anthropic_module, create=True),
        pytest.raises(LLMStatusError) as exc_info,
    ):
        await llm.generate(MockPrompt("Hello!"))
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


async def test_streaming_yields_text_chunks():
    """_call_streaming yields response and usage chunks."""

    async def fake_stream() -> AsyncIterator[MagicMock]:
        # message_start event
        e1 = MagicMock()
        e1.type = "message_start"
        e1.message = MagicMock()
        e1.message.usage = MagicMock()
        e1.message.usage.input_tokens = 5
        yield e1

        # content_block_start for text
        e2 = MagicMock()
        e2.type = "content_block_start"
        e2.index = 0
        e2.content_block = MagicMock()
        e2.content_block.type = "text"
        yield e2

        # content_block_delta (text)
        for text in ["Hello", " world!"]:
            e = MagicMock()
            e.type = "content_block_delta"
            e.index = 0
            e.delta = MagicMock()
            e.delta.type = "text_delta"
            e.delta.text = text
            yield e

        # message_delta with usage
        e_delta = MagicMock()
        e_delta.type = "message_delta"
        e_delta.usage = MagicMock()
        e_delta.usage.output_tokens = 10
        yield e_delta

    # Patch anthropic exceptions so _call_streaming's try/except works
    class FakeBaseError(Exception):
        pass

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.APIConnectionError = FakeBaseError
    mock_anthropic_module.APIStatusError = FakeBaseError
    mock_anthropic_module.APIResponseValidationError = FakeBaseError

    llm = _make_llm()
    llm._client.messages.create = AsyncMock(return_value=fake_stream())  # type: ignore[method-assign]

    with patch("ragbits.core.llms.anthropic.anthropic", mock_anthropic_module, create=True):
        generator = await llm._call_streaming(MockPrompt("Hi!"), llm.default_options)
        chunks = [chunk async for chunk in generator]

    text_chunks = [c for c in chunks if "response" in c and not c.get("reasoning")]
    usage_chunks = [c for c in chunks if "usage" in c]

    assert "".join(c["response"] for c in text_chunks) == "Hello world!"
    assert len(usage_chunks) == 1
    assert usage_chunks[0]["usage"]["prompt_tokens"] == 5
    assert usage_chunks[0]["usage"]["completion_tokens"] == 10
