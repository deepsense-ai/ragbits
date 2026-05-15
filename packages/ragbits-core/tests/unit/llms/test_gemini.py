import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_genai_types():
    mock_types = MagicMock()
    mock_types.Content.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_types.Part.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_types.FunctionCall.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_types.FunctionResponse.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_types.FunctionDeclaration.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_types.Part.from_bytes = MagicMock(return_value=SimpleNamespace(text=None, function_call=None))
    with patch("ragbits.core.llms.gemini.genai_types", mock_types):
        yield mock_types


from ragbits.core.llms.exceptions import (  # noqa: E402
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMStatusError,
)
from ragbits.core.llms.gemini import GeminiLLM, GeminiLLMOptions  # noqa: E402
from ragbits.core.prompt.base import BasePrompt, ChatFormat  # noqa: E402


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


def _make_text_part(text: str) -> MagicMock:
    part = MagicMock()
    part.text = text
    part.function_call = None
    return part


def _make_function_call_part(name: str, args: dict[str, object]) -> MagicMock:
    fc = MagicMock()
    fc.name = name
    fc.args = args

    part = MagicMock()
    part.text = None
    part.function_call = fc
    return part


def _make_gemini_response(parts: list, prompt_tokens: int = 10, completion_tokens: int = 20) -> MagicMock:
    content = MagicMock()
    content.parts = parts

    candidate = MagicMock()
    candidate.content = content

    usage = MagicMock()
    usage.prompt_token_count = prompt_tokens
    usage.candidates_token_count = completion_tokens
    usage.total_token_count = prompt_tokens + completion_tokens

    response = MagicMock()
    response.candidates = [candidate]
    response.usage_metadata = usage
    return response


def get_weather(location: str) -> str:
    """Returns the current weather for a given location."""
    return json.dumps({"location": location, "temperature": "72"})


def _make_llm(model_name: str = "gemini-2.5-flash", **kwargs: Any) -> GeminiLLM:
    """Create a GeminiLLM with a stub client (no real google-genai SDK needed)."""
    mock_client = MagicMock()
    with (
        patch("ragbits.core.llms.gemini.HAS_GOOGLE_GENAI", True),
        patch("ragbits.core.llms.gemini.genai", create=True) as mock_genai,
    ):
        mock_genai.Client.return_value = mock_client
        llm = GeminiLLM(model_name=model_name, api_key="test-key", **kwargs)
    return llm


# ---------------------------------------------------------------------------
# Basic generation
# ---------------------------------------------------------------------------


async def test_generation():
    """Basic text generation."""
    llm = _make_llm()
    llm._client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_gemini_response([_make_text_part("I'm fine, thank you.")])
    )

    result = await llm.generate(MockPrompt("Hello, how are you?"))

    assert result == "I'm fine, thank you."


async def test_generation_with_metadata():
    """generate_with_metadata returns content and token usage."""
    llm = _make_llm()
    llm._client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_gemini_response(
            [_make_text_part("Great!")],
            prompt_tokens=5,
            completion_tokens=15,
        )
    )

    output = await llm.generate_with_metadata(MockPrompt("Hello!"))

    assert output.content == "Great!"
    assert output.usage is not None
    assert output.usage.prompt_tokens == 5
    assert output.usage.completion_tokens == 15
    assert output.usage.total_tokens == 20


async def test_generation_with_tools():
    """Tool calls are returned when the model calls a function."""
    llm = _make_llm()
    llm._client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_gemini_response([_make_function_call_part("get_weather", {"location": "San Francisco"})])
    )

    result = await llm.generate(MockPrompt("Weather?"), tools=[get_weather])

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "get_weather"
    assert result[0].type == "function"


async def test_generation_with_duplicate_tool_calls_gets_unique_ids():
    """Multiple calls to the same function get unique IDs."""
    llm = _make_llm()
    llm._client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_gemini_response(
            [
                _make_function_call_part("get_weather", {"location": "San Francisco"}),
                _make_function_call_part("get_weather", {"location": "Warsaw"}),
            ]
        )
    )

    result = await llm.generate(MockPrompt("Weather?"), tools=[get_weather])

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].id != result[1].id
    assert result[0].arguments == {"location": "San Francisco"}
    assert result[1].arguments == {"location": "Warsaw"}


async def test_generation_with_tools_no_tool_used():
    """Plain text is returned when no tool is called."""
    llm = _make_llm()
    llm._client.aio.models.generate_content = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_gemini_response([_make_text_part("I don't need tools.")])
    )

    result = await llm.generate(MockPrompt("Hello!"), tools=[get_weather])

    assert isinstance(result, str)
    assert result == "I don't need tools."


async def test_empty_candidates_raises():
    """Empty candidates list raises LLMEmptyResponseError."""
    llm = _make_llm()
    empty_response = MagicMock()
    empty_response.candidates = []
    llm._client.aio.models.generate_content = AsyncMock(return_value=empty_response)  # type: ignore[method-assign]

    with pytest.raises(LLMEmptyResponseError):
        await llm.generate(MockPrompt("Hello!"))


async def test_empty_parts_raises():
    """Candidate with no content parts raises LLMEmptyResponseError."""
    llm = _make_llm()
    content = MagicMock()
    content.parts = []
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    llm._client.aio.models.generate_content = AsyncMock(return_value=response)  # type: ignore[method-assign]

    with pytest.raises(LLMEmptyResponseError):
        await llm.generate(MockPrompt("Hello!"))


def test_get_model_id():
    llm = _make_llm(model_name="gemini-2.5-flash")
    assert llm.get_model_id() == "gemini:gemini-2.5-flash"


def test_common_options_are_sent_to_gemini_api(mock_genai_types: MagicMock):
    llm = _make_llm()

    llm._build_config(
        system=None,
        options=GeminiLLMOptions(max_tokens=100, temperature=0.5, top_p=0.8),
        tools=None,
        tool_choice=None,
    )

    config_kwargs = mock_genai_types.GenerateContentConfig.call_args.kwargs
    assert config_kwargs["max_output_tokens"] == 100
    assert config_kwargs["temperature"] == 0.5
    assert config_kwargs["top_p"] == 0.8


# ---------------------------------------------------------------------------
# _convert_messages tests
# ---------------------------------------------------------------------------


def test_convert_messages_extracts_system():
    """System messages are extracted as a separate string."""
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
    ]
    system, contents = GeminiLLM._convert_messages(messages)
    assert system == "You are helpful."
    assert len(contents) == 1


def test_convert_messages_tool_results_grouped():
    """Consecutive tool messages are merged into a single user Content."""
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
    _, contents = GeminiLLM._convert_messages(messages)
    # Should produce: 1 model Content + 1 user Content (both tool results)
    assert len(contents) == 2
    assert contents[0].role == "model"
    assert contents[1].role == "user"
    # Both tool results in the same user Content
    assert contents[1].parts is not None
    assert len(contents[1].parts) == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_api_call_error():
    """GoogleAPICallError is wrapped as LLMStatusError."""
    llm = _make_llm()

    class MockGoogleAPICallError(Exception):
        def __init__(self, message: str, code: int) -> None:
            super().__init__(message)
            self.code = code

    exc = MockGoogleAPICallError("not found", 404)
    llm._client.aio.models.generate_content = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

    with patch("ragbits.core.llms.gemini.google_exceptions") as mock_google_exc:
        mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
        mock_google_exc.GoogleAPIError = Exception
        with pytest.raises(LLMStatusError) as exc_info:
            await llm.generate(MockPrompt("Hello!"))

    assert exc_info.value.status_code == 404


async def test_generic_api_error():
    """GoogleAPIError (non-call) is wrapped as LLMConnectionError."""
    llm = _make_llm()

    class MockGoogleAPIError(Exception):
        pass

    class MockGoogleAPICallError(MockGoogleAPIError):
        pass

    exc = MockGoogleAPIError("connection failed")
    llm._client.aio.models.generate_content = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

    with patch("ragbits.core.llms.gemini.google_exceptions") as mock_google_exc:
        mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
        mock_google_exc.GoogleAPIError = MockGoogleAPIError
        with pytest.raises(LLMConnectionError):
            await llm.generate(MockPrompt("Hello!"))


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


async def test_streaming_yields_text_chunks():
    """_call_streaming yields response chunks then a usage dict."""
    llm = _make_llm()

    async def fake_stream() -> AsyncIterator[MagicMock]:
        for text in ["Hello", " world!"]:
            part = _make_text_part(text)
            content = MagicMock()
            content.parts = [part]
            candidate = MagicMock()
            candidate.content = content
            chunk = MagicMock()
            chunk.candidates = [candidate]
            usage = MagicMock()
            usage.prompt_token_count = 5
            usage.candidates_token_count = 2
            chunk.usage_metadata = usage
            yield chunk

    llm._client.aio.models.generate_content_stream = AsyncMock(return_value=fake_stream())  # type: ignore[method-assign]

    generator = await llm._call_streaming(MockPrompt("Hi!"), llm.default_options)
    chunks = [chunk async for chunk in generator]

    text_chunks = [c for c in chunks if "response" in c]
    usage_chunks = [c for c in chunks if "usage" in c]

    assert "".join(c["response"] for c in text_chunks) == "Hello world!"
    assert len(usage_chunks) == 1
