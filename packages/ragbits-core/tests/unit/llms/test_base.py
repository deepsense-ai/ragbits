import json
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from ragbits.core.audit.metrics import MetricHandler, set_metric_handlers
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.audit.traces import TraceHandler, set_trace_handlers
from ragbits.core.llms.base import LLMResponseWithMetadata, Reasoning, ToolCall, Usage, UsageItem
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, ChatFormat, SimplePrompt


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


@pytest.fixture(name="llm_with_reasoning")
def mock_llm_with_reasoning() -> MockLLM:
    llm_options = MockLLMOptions(
        response="test response",
        response_stream=["first response", "second response"],
        reasoning="Reasoning",
        reasoning_stream=["Reasoning 1", "Reasoning 2"],
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


@pytest.fixture(name="get_weather_schema")
def mock_get_weather_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Returns the current weather for a given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "description": "The location to get the weather for.",
                        "title": "Location",
                        "type": "string",
                    }
                },
                "required": ["location"],
            },
        },
    }


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
    assert response == {
        "response": "test response",
        "tool_calls": None,
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 30,
            "completion_tokens": 20,
        },
        "throughput": 1,
    }


async def test_generate_raw_with_chat_format(llm: MockLLM):
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    response = await llm.generate_raw(chat)
    assert response == {
        "response": "test response",
        "tool_calls": None,
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 30,
            "completion_tokens": 20,
        },
        "throughput": 1,
    }


async def test_generate_raw_with_base_prompt(llm: MockLLM):
    prompt = SimplePrompt("Hello")
    response = await llm.generate_raw(prompt)
    assert response == {
        "response": "test response",
        "tool_calls": None,
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 30,
            "completion_tokens": 20,
        },
        "throughput": 1,
    }


@pytest.mark.parametrize(
    "prompt",
    [
        "Hello",
        [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}],
        SimplePrompt("Hello"),
    ],
    ids=["string", "chat_format", "base_prompt"],
)
async def test_generate_metadata(llm: MockLLM, prompt: str | ChatFormat | BasePrompt):
    """Test generate_with_metadata with different prompt types."""
    response = await llm.generate_with_metadata(prompt)
    assert isinstance(response, LLMResponseWithMetadata)
    assert response.content == "test response"
    assert response.reasoning is None
    assert response.metadata == {
        "is_mocked": True,
        "throughput": 1,
    }
    assert response.usage == Usage(
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


async def test_generate_metadata_with_reasoning(llm_with_reasoning: MockLLM):
    response = await llm_with_reasoning.generate_with_metadata("Hello")
    assert response.reasoning == "Reasoning"


async def test_generate_metadata_with_base_prompt_list(llm: MockLLM):
    prompt: list[BasePrompt] = [SimplePrompt("Hello"), SimplePrompt("Hello")]
    responses = await llm.generate_with_metadata(prompt)
    for i, response in enumerate(responses):
        assert isinstance(response, LLMResponseWithMetadata)
        assert response.content == "test response"
        assert response.metadata == {
            "is_mocked": True,
            "throughput": 0.5,
        }
        assert response.usage == Usage(
            requests=[
                UsageItem(
                    model="mock:mock",
                    prompt_tokens=10 * (i + 1),
                    completion_tokens=20 * (i + 1),
                    total_tokens=30 * (i + 1),
                    estimated_cost=0.0,
                )
            ]
        )


async def test_generate_metadata_with_parser_prompt(llm: MockLLM):
    prompt = CustomPrompt("Hello")
    response = await llm.generate_with_metadata(prompt)
    assert isinstance(response, LLMResponseWithMetadata)
    assert isinstance(response.content, CustomOutputType)
    assert response.content.message == "test response"
    assert response.metadata == {
        "is_mocked": True,
        "throughput": 1,
    }
    assert response.usage == Usage(
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


@pytest.mark.parametrize(
    "prompt",
    [
        "Hello",
        [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}],
        SimplePrompt("Hello"),
    ],
    ids=["string", "chat_format", "base_prompt"],
)
async def test_generate_stream(llm: MockLLM, prompt: str | ChatFormat | BasePrompt):
    """Test generate_streaming with different prompt types."""
    stream = llm.generate_streaming(prompt)
    assert [response async for response in stream] == ["first response", "second response"]


async def test_generate_stream_with_reasoning(llm_with_reasoning: MockLLM):
    stream = llm_with_reasoning.generate_streaming("Hello")
    assert [response async for response in stream] == [
        Reasoning("Reasoning 1"),
        Reasoning("Reasoning 2"),
        "first response",
        "second response",
    ]
    assert stream.metadata.reasoning == "Reasoning 1Reasoning 2"


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


async def test_generate_with_tool_choice_str(llm_with_tools: MockLLM):
    await llm_with_tools.generate("Hello", tools=[get_weather], tool_choice="auto")
    assert llm_with_tools.tool_choice == "auto"


async def test_generate_with_tool_choice_dict(llm_with_tools: MockLLM):
    tool_choice = {"type": "function", "function": {"name": "get_weather"}}
    await llm_with_tools.generate("Hello", tools=[get_weather], tool_choice=tool_choice)
    assert llm_with_tools.tool_choice == tool_choice


async def test_generate_with_tool_choice_callable(llm_with_tools: MockLLM, get_weather_schema: dict):
    await llm_with_tools.generate("Hello", tools=[get_weather], tool_choice=get_weather)
    assert llm_with_tools.tool_choice == get_weather_schema


async def test_generate_streaming_with_tool_choice_str(llm_with_tools: MockLLM):
    stream = llm_with_tools.generate_streaming("Hello", tools=[get_weather], tool_choice="auto")
    async for _ in stream:
        pass
    assert llm_with_tools.tool_choice == "auto"


async def test_generate_streaming_with_tool_choice_dict(llm_with_tools: MockLLM):
    tool_choice = {"type": "function", "function": {"name": "get_weather"}}
    stream = llm_with_tools.generate_streaming("Hello", tools=[get_weather], tool_choice=tool_choice)
    async for _ in stream:
        pass
    assert llm_with_tools.tool_choice == tool_choice


async def test_generate_streaming_with_tool_choice_callable(llm_with_tools: MockLLM, get_weather_schema: dict):
    stream = llm_with_tools.generate_streaming("Hello", tools=[get_weather], tool_choice=get_weather)
    async for _ in stream:
        pass
    assert llm_with_tools.tool_choice == get_weather_schema


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


@pytest.fixture
def mock_metric_handler():
    handler = MagicMock(spec=MetricHandler)
    handler.create_histogram = MagicMock()
    handler.record = MagicMock()
    return handler


@pytest.fixture
def mock_trace_handler():
    handler = MagicMock(spec=TraceHandler)
    handler.start = MagicMock(return_value=MagicMock())
    handler.stop = MagicMock()
    return handler


async def test_generate_with_metadata_tracing_and_metrics(
    llm: MockLLM, mock_metric_handler: MagicMock, mock_trace_handler: MagicMock
):
    set_metric_handlers(mock_metric_handler)
    set_trace_handlers(mock_trace_handler)

    prompts: list[BasePrompt] = [SimplePrompt("Hello"), SimplePrompt("Hello")]
    await llm.generate_with_metadata(prompts)

    mock_trace_handler.trace.assert_called_once_with(
        "generate", model_name=llm.model_name, prompt=prompts, options="None"
    )

    metric_calls = mock_metric_handler.record_metric.call_args_list
    assert len(metric_calls) == 3
    print(metric_calls)
    assert metric_calls[0][1]["metric_key"] == LLMMetric.INPUT_TOKENS
    assert metric_calls[0][1]["value"] == 30
    assert metric_calls[0][1]["attributes"]["model"] == llm.model_name
    assert metric_calls[0][1]["metric_type"] == MetricType.HISTOGRAM

    assert metric_calls[1][1]["metric_key"] == LLMMetric.PROMPT_THROUGHPUT
    assert metric_calls[1][1]["value"] == 1.0
    assert metric_calls[1][1]["attributes"]["model"] == llm.model_name
    assert metric_calls[1][1]["metric_type"] == MetricType.HISTOGRAM

    assert metric_calls[2][1]["metric_key"] == LLMMetric.TOKEN_THROUGHPUT
    assert metric_calls[2][1]["value"] == 90.0  # total_tokens / throughput
    assert metric_calls[2][1]["attributes"]["model"] == llm.model_name
    assert metric_calls[2][1]["metric_type"] == MetricType.HISTOGRAM


async def test_generate_streaming_trace_handler_closes_properly(llm: MockLLM, mock_trace_handler: MagicMock):
    set_trace_handlers(mock_trace_handler)

    prompt = SimplePrompt("Hello")
    stream = llm.generate_streaming(prompt)

    responses = [response async for response in stream]
    assert responses == ["first response", "second response"]

    # Verify trace context manager was called and properly exited
    mock_trace_handler.trace.assert_called_once()
    # The context manager's __enter__ and __exit__ should both be called
    trace_cm = mock_trace_handler.trace.return_value
    trace_cm.__enter__.assert_called_once()
    trace_cm.__exit__.assert_called_once()
