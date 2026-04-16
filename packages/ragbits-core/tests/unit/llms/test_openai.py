import json
from collections.abc import AsyncIterator
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from ragbits.core.llms.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMStatusError,
)
from ragbits.core.llms.openai import OpenAILLM, OpenAILLMOptions
from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, ChatFormat


class MockPrompt(BasePrompt):
    def __init__(self, message: str):
        self.message = message

    @property
    def chat(self) -> ChatFormat:
        return [{"content": self.message, "role": "user"}]


class MockPromptWithParser(BasePromptWithParser[int]):
    def __init__(self, message: str):
        self.message = message

    @property
    def chat(self) -> ChatFormat:
        return [{"content": self.message, "role": "user"}]

    @staticmethod
    async def parse_response(response: str) -> int:
        return 42


def _make_openai_response(
    content: str | None,
    tool_calls: list[MagicMock] | None = None,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> MagicMock:
    """Build a minimal mock that looks like an openai ChatCompletion response."""
    message = MagicMock()
    message.content = content
    message.reasoning_content = None
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message
    choice.logprobs = None

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _make_tool_call(name: str, arguments: str, id: str = "call_123") -> MagicMock:
    func = MagicMock()
    func.name = name
    func.arguments = arguments

    tc = MagicMock()
    tc.function = func
    tc.type = "function"
    tc.id = id
    return tc


def get_weather(location: str) -> str:
    """Returns the current weather for a given location."""
    return json.dumps({"location": location, "temperature": "72"})


async def test_generation():
    """Basic text generation."""
    llm = OpenAILLM(api_key="test-key")
    llm._get_openai_response = AsyncMock(return_value=_make_openai_response("I'm fine, thank you."))  # type: ignore[method-assign]

    result = await llm.generate(MockPrompt("Hello, how are you?"))

    assert result == "I'm fine, thank you."


async def test_generation_with_parser():
    """Generation with a prompt parser returns the parsed result."""
    llm = OpenAILLM(api_key="test-key")
    llm._get_openai_response = AsyncMock(return_value=_make_openai_response("irrelevant"))  # type: ignore[method-assign]

    result = await llm.generate(MockPromptWithParser("What is 6x7?"))

    assert result == 42


async def test_generation_with_metadata():
    """generate_with_metadata returns content and token usage."""
    llm = OpenAILLM(api_key="test-key")
    llm._get_openai_response = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_openai_response("Great!", prompt_tokens=5, completion_tokens=15)
    )

    output = await llm.generate_with_metadata(MockPrompt("Hello!"))

    assert output.content == "Great!"
    assert output.usage is not None
    assert output.usage.prompt_tokens == 5
    assert output.usage.completion_tokens == 15
    assert output.usage.total_tokens == 20


async def test_generation_with_tools():
    """Tool calls are returned when tools are provided and the model calls one."""
    llm = OpenAILLM(api_key="test-key")
    response = _make_openai_response(
        content=None, tool_calls=[_make_tool_call("get_weather", '{"location":"San Francisco"}', "call_abc")]
    )
    response.choices[0].message.content = None
    llm._get_openai_response = AsyncMock(return_value=response)  # type: ignore[method-assign]

    result = await llm.generate(MockPrompt("What is the weather in San Francisco?"), tools=[get_weather])

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "get_weather"
    assert result[0].id == "call_abc"
    assert result[0].type == "function"
    assert result[0].arguments == {"location": "San Francisco"}


async def test_generation_with_tools_no_tool_used():
    """Plain text response when tools are available but not called."""
    llm = OpenAILLM(api_key="test-key")
    response = _make_openai_response("I don't need any tools.")
    response.choices[0].message.tool_calls = None
    llm._get_openai_response = AsyncMock(return_value=response)  # type: ignore[method-assign]

    result = await llm.generate(MockPrompt("Hello!"), tools=[get_weather])

    assert isinstance(result, str)
    assert result == "I don't need any tools."


async def test_empty_response_raises():
    """Empty choices list raises LLMEmptyResponseError."""
    llm = OpenAILLM(api_key="test-key")
    empty_response = MagicMock()
    empty_response.choices = []
    llm._get_openai_response = AsyncMock(return_value=empty_response)  # type: ignore[method-assign]

    with pytest.raises(LLMEmptyResponseError):
        await llm.generate(MockPrompt("Hello!"))


@patch("ragbits.core.llms.openai.openai")
async def test_api_connection_error(mock_openai: MagicMock):
    """APIConnectionError is wrapped as LLMConnectionError."""

    class FakeBase(Exception):
        pass

    class FakeConnectionError(FakeBase):
        pass

    class FakeStatusError(FakeBase):
        def __init__(
            self, message: str, status_code: int = 500, response: object | None = None, body: object | None = None
        ):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    mock_openai.APIConnectionError = FakeConnectionError
    mock_openai.APIStatusError = FakeStatusError
    mock_openai.APIResponseValidationError = FakeBase

    llm = OpenAILLM(api_key="test-key")
    llm._client = MagicMock()
    llm._client.chat.completions.create = AsyncMock(side_effect=FakeConnectionError("timeout"))

    with pytest.raises(LLMConnectionError):
        await llm.generate(MockPrompt("Hello!"))


@patch("ragbits.core.llms.openai.openai")
async def test_api_status_error(mock_openai: MagicMock):
    """APIStatusError is wrapped as LLMStatusError."""

    class FakeBase(Exception):
        pass

    class FakeConnectionError(FakeBase):
        pass

    class FakeStatusError(FakeBase):
        def __init__(
            self, message: str, status_code: int = 500, response: object | None = None, body: object | None = None
        ):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    mock_openai.APIConnectionError = FakeConnectionError
    mock_openai.APIStatusError = FakeStatusError
    mock_openai.APIResponseValidationError = FakeBase

    llm = OpenAILLM(api_key="test-key")
    llm._client = MagicMock()
    llm._client.chat.completions.create = AsyncMock(side_effect=FakeStatusError("rate limited", status_code=429))

    with pytest.raises(LLMStatusError) as exc_info:
        await llm.generate(MockPrompt("Hello!"))
    assert exc_info.value.status_code == 429


async def test_get_model_id():
    llm = OpenAILLM(model_name="gpt-4o", api_key="test-key")
    assert llm.get_model_id() == "openai:gpt-4o"


async def test_options_are_passed_to_api():
    """Options that are set get included in the API call."""
    llm = OpenAILLM(api_key="test-key")
    llm._get_openai_response = AsyncMock(return_value=_make_openai_response("ok"))  # type: ignore[method-assign]
    options = OpenAILLMOptions(temperature=0.5, max_tokens=100)

    await llm.generate(MockPrompt("Hello!"), options=options)

    call_kwargs = llm._get_openai_response.call_args.kwargs
    assert call_kwargs["options"].temperature == 0.5
    assert call_kwargs["options"].max_tokens == 100


class MockSchema(BaseModel):
    answer: str


def test_structured_output_produces_json_schema_format():
    """use_structured_output=True wraps Pydantic model in json_schema response_format."""
    llm = OpenAILLM(api_key="test-key", use_structured_output=True)
    result = llm._get_response_format(output_schema=MockSchema, json_mode=True)

    assert result is not None
    assert result["type"] == "json_schema"
    assert result["json_schema"]["name"] == "MockSchema"
    assert "properties" in result["json_schema"]["schema"]


def test_json_mode_fallback_without_structured_output():
    """Without use_structured_output, json_mode falls back to json_object."""
    llm = OpenAILLM(api_key="test-key", use_structured_output=False)
    result = llm._get_response_format(output_schema=MockSchema, json_mode=True)

    assert result == {"type": "json_object"}


async def test_streaming_yields_text_chunks():
    """_call_streaming yields response chunks then a usage dict."""

    async def fake_stream() -> AsyncIterator[MagicMock]:
        for text in ["Hello", ", ", "world!"]:
            delta = MagicMock()
            delta.content = text
            delta.reasoning_content = None
            delta.tool_calls = None
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            chunk.usage = None
            yield chunk

        # Final chunk with usage, no choices
        usage = MagicMock()
        usage.prompt_tokens = 5
        usage.completion_tokens = 3
        usage.total_tokens = 8
        final_chunk = MagicMock()
        final_chunk.choices = []
        final_chunk.usage = usage
        yield final_chunk

    llm = OpenAILLM(api_key="test-key")
    llm._get_openai_response = AsyncMock(return_value=fake_stream())  # type: ignore[method-assign]

    generator = await llm._call_streaming(MockPrompt("Hi!"), llm.default_options)
    chunks = [chunk async for chunk in generator]

    text_chunks = [c for c in chunks if "response" in c]
    usage_chunks = [c for c in chunks if "usage" in c]

    assert "".join(c["response"] for c in text_chunks) == "Hello, world!"
    assert len(usage_chunks) == 1
    assert usage_chunks[0]["usage"]["prompt_tokens"] == 5
    assert usage_chunks[0]["usage"]["completion_tokens"] == 3


async def test_pdf_url_attachment_is_uploaded_and_replaced_with_file_id():
    llm = OpenAILLM(api_key="test-key")
    llm._client = MagicMock()
    llm._client.chat.completions.create = AsyncMock(return_value=_make_openai_response("ok"))
    llm._client.files.create = AsyncMock(return_value=MagicMock(id="file-uploaded-123"))
    llm._client.files.delete = AsyncMock(return_value=MagicMock())
    llm._download_url_as_bytes = AsyncMock(return_value=b"%PDF-1.4")  # type: ignore[method-assign]

    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Question: summarize this file"},
                {"type": "file", "file": {"file_id": "https://example.com/test.pdf"}},
            ],
        }
    ]
    original = deepcopy(conversation)

    await llm._get_openai_response(
        conversation=conversation,
        options=llm.default_options,
    )

    call_kwargs = llm._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"][0]["content"][1]["file"]["file_id"] == "file-uploaded-123"
    assert conversation == original
    llm._client.files.delete.assert_awaited_once_with("file-uploaded-123")


async def test_pdf_file_data_attachment_is_uploaded_and_replaced_with_file_id():
    llm = OpenAILLM(api_key="test-key")
    llm._client = MagicMock()
    llm._client.chat.completions.create = AsyncMock(return_value=_make_openai_response("ok"))
    llm._client.files.create = AsyncMock(return_value=MagicMock(id="file-uploaded-xyz"))
    llm._client.files.delete = AsyncMock(return_value=MagicMock())

    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Question: summarize this file"},
                {"type": "file", "file": {"file_data": "data:application/pdf;base64,JVBERi0xLjQK"}},
            ],
        }
    ]

    await llm._get_openai_response(
        conversation=conversation,
        options=llm.default_options,
    )

    call_kwargs = llm._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"][0]["content"][1]["file"]["file_id"] == "file-uploaded-xyz"
    llm._client.files.delete.assert_awaited_once_with("file-uploaded-xyz")
