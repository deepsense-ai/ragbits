import json

import pytest
from pydantic import BaseModel

from ragbits.core.llms.base import LLMResponseWithMetadata, ToolCall
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.core.prompt.base import BasePromptWithParser, ChatFormat, SimplePrompt


class CustomOutputType(BaseModel):
    message: str


@pytest.fixture(name="llm")
def mock_llm() -> MockLLM:
    llm_options = MockLLMOptions(
        response="test response",
        response_stream=["first response", "second response"],
    )
    return MockLLM(default_options=llm_options)


@pytest.fixture(name="llm_with_tools")
def mock_llm_with_tools() -> MockLLM:
    llm_options = MockLLMOptions(
        tool_calls=[
            {
                "id": "call_Dq3XWqfuMskh9SByzz5g00mM",
                "type": "function",
                "name": "get_weather",
                "arguments": '{"location":"San Francisco"}',
            }
        ]
    )
    return MockLLM(default_options=llm_options)


class CustomPrompt(BasePromptWithParser[CustomOutputType]):
    def __init__(self, content: str) -> None:
        self._content = content

    @property
    def chat(self) -> ChatFormat:
        return [{"role": "user", "content": self._content}]

    @staticmethod
    async def parse_response(response: str) -> CustomOutputType:
        return CustomOutputType(message=response)


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


async def test_generate_with_str(llm: MockLLM):
    response = await llm.generate("Hello")
    assert response == "test response"


async def test_generate_with_chat_format(llm: MockLLM):
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    response = await llm.generate(chat)
    assert response == "test response"


async def test_generate_with_base_prompt(llm: MockLLM):
    prompt = SimplePrompt("Hello")
    response = await llm.generate(prompt)
    assert response == "test response"


async def test_generate_with_parser_prompt(llm: MockLLM):
    prompt = CustomPrompt("Hello")
    response = await llm.generate(prompt)
    assert isinstance(response, CustomOutputType)
    assert response.message == "test response"


async def test_generate_raw_with_str(llm: MockLLM):
    response = await llm.generate_raw("Hello")
    assert response == {"response": "test response", "tool_calls": None, "is_mocked": True}


async def test_generate_raw_with_chat_format(llm: MockLLM):
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    response = await llm.generate_raw(chat)
    assert response == {"response": "test response", "tool_calls": None, "is_mocked": True}


async def test_generate_raw_with_base_prompt(llm: MockLLM):
    prompt = SimplePrompt("Hello")
    response = await llm.generate_raw(prompt)
    assert response == {"response": "test response", "tool_calls": None, "is_mocked": True}


async def test_generate_metadata_with_str(llm: MockLLM):
    response = await llm.generate_with_metadata("Hello")
    assert isinstance(response, LLMResponseWithMetadata)
    assert response.content == "test response"
    assert response.metadata == {"is_mocked": True}


async def test_generate_metadata_with_chat_format(llm: MockLLM):
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    response = await llm.generate_with_metadata(chat)
    assert isinstance(response, LLMResponseWithMetadata)
    assert response.content == "test response"
    assert response.metadata == {"is_mocked": True}


async def test_generate_metadata_with_base_prompt(llm: MockLLM):
    prompt = SimplePrompt("Hello")
    response = await llm.generate_with_metadata(prompt)
    assert isinstance(response, LLMResponseWithMetadata)
    assert response.content == "test response"
    assert response.metadata == {"is_mocked": True}


async def test_generate_metadata_with_parser_prompt(llm: MockLLM):
    prompt = CustomPrompt("Hello")
    response = await llm.generate_with_metadata(prompt)
    assert isinstance(response, LLMResponseWithMetadata)
    assert isinstance(response.content, CustomOutputType)
    assert response.content.message == "test response"
    assert response.metadata == {"is_mocked": True}


async def test_generate_stream_with_str(llm: MockLLM):
    stream = llm.generate_streaming("Hello")
    assert [response async for response in stream] == ["first response", "second response"]


async def test_generate_stream_with_chat_format(llm: MockLLM):
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    stream = llm.generate_streaming(chat)
    assert [response async for response in stream] == ["first response", "second response"]


async def test_generate_stream_with_base_prompt(llm: MockLLM):
    prompt = SimplePrompt("Hello")
    stream = llm.generate_streaming(prompt)
    assert [response async for response in stream] == ["first response", "second response"]


async def test_generate_stream_with_tools_output(llm_with_tools: MockLLM):
    stream = llm_with_tools.generate_streaming("Hello", tools=[get_weather])
    assert [response async for response in stream] == [
        ToolCall(  # type: ignore
            arguments='{"location":"San Francisco"}',  # type: ignore
            name="get_weather",
            id="call_Dq3XWqfuMskh9SByzz5g00mM",
            type="function",
        )
    ]


async def test_generate_stream_with_tools_output_no_tool_used(llm: MockLLM):
    stream = llm.generate_streaming("Hello", tools=[get_weather])
    assert [response async for response in stream] == ["first response", "second response"]


def test_init_with_str():
    prompt = SimplePrompt("Hello")
    assert prompt.chat == [{"role": "user", "content": "Hello"}]


def test_init_with_chat_format():
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    prompt = SimplePrompt(chat)
    assert prompt.chat == chat


def test_json_mode():
    prompt = SimplePrompt("Hello")
    assert prompt.json_mode is False


def test_output_schema():
    prompt = SimplePrompt("Hello")
    assert prompt.output_schema() is None


def test_has_images():
    prompt = SimplePrompt("Hello")
    assert len(prompt.list_images()) == 0


def test_get_token_id(llm: MockLLM):
    with pytest.raises(NotImplementedError):
        llm.get_token_id("example_token")
