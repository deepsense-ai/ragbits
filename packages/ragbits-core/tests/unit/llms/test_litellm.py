import json
import pickle
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm import Message, Router, Usage
from litellm.types.utils import ChatCompletionMessageToolCall, Choices, Function, ModelResponse
from pydantic import BaseModel

from ragbits.core.llms.base import ToolCall
from ragbits.core.llms.exceptions import LLMNotSupportingImagesError, LLMNotSupportingToolUseError
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.prompt import Prompt
from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, ChatFormat
from ragbits.core.utils.function_schema import convert_function_to_function_schema


class MockPrompt(BasePrompt):
    """
    Mock prompt for testing LiteLLM.
    """

    def __init__(self, message: str):
        """
        Constructs a new MockPrompt instance.

        Args:
            message: Message to be used in the prompt.
        """
        self.message = message

    @property
    def chat(self) -> ChatFormat:
        """
        Chat content of the prompt.

        Returns:
            Chat content of the prompt.
        """
        return [{"content": self.message, "role": "user"}]


class MockPromptWithParser(BasePromptWithParser[int]):
    """
    Mock prompt for testing LiteLLM.
    """

    def __init__(self, message: str):
        """
        Constructs a new MockPrompt instance.

        Args:
            message: Message to be used in the prompt.
        """
        self.message = message

    @property
    def chat(self) -> ChatFormat:
        """
        Chat content of the prompt.

        Returns:
            Chat content of the prompt.
        """
        return [{"content": self.message, "role": "user"}]

    @staticmethod
    async def parse_response(response: str) -> int:
        """
        Parser for the prompt.

        Args:
            response: Response to parse.

        Returns:
            Parser for the prompt.
        """
        return 42


class MockPromptWithImage(MockPrompt):
    """
    Mock prompt for testing LiteLLM.
    """

    def list_images(self) -> list[str]:  # noqa: PLR6301
        """
        Returns whether the prompt has images.
        """
        return ["fake_image_url"]


def mock_llm_responses_with_tool(llm: LiteLLM):
    llm._get_litellm_response = AsyncMock()  # type: ignore
    llm._get_litellm_response.side_effect = [
        ModelResponse(
            choices=[
                Choices(
                    message=Message(
                        content=None,
                        role="assistant",
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                function=Function(arguments='{"location":"San Francisco"}', name="get_weather"),
                                id="call_Dq3XWqfuMskh9SByzz5g00mM",
                                type="function",
                            )
                        ],
                    ),
                )
            ],
            usage=Usage(
                completion_tokens=10,
                prompt_tokens=20,
                total_tokens=30,
            ),
        ),
    ]


def mock_llm_responses_with_tool_no_tool_used(llm: LiteLLM):
    llm._get_litellm_response = AsyncMock()  # type: ignore
    llm._get_litellm_response.side_effect = [
        ModelResponse(
            choices=[
                Choices(
                    message=Message(content="I'm fine.", role="assistant", tool_calls=None),
                )
            ],
            usage=Usage(
                completion_tokens=10,
                prompt_tokens=20,
                total_tokens=30,
            ),
        ),
    ]


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


async def test_generation():
    """Test generation of a response."""
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, how are you?")
    options = LiteLLMOptions(mock_response="I'm fine, thank you.")
    output = await llm.generate(prompt, options=options)
    assert output == "I'm fine, thank you."


async def test_generation_with_parser():
    """Test generation of a response with a parser."""
    llm = LiteLLM(api_key="test_key")
    prompt = MockPromptWithParser("Hello, how are you?")
    options = LiteLLMOptions(mock_response="I'm fine, thank you.")
    output = await llm.generate(prompt, options=options)
    assert output == 42
    raw_output = await llm.generate_raw(prompt, options=options)
    assert raw_output["response"] == "I'm fine, thank you."


@patch("litellm.supports_function_calling")
async def test_generation_with_tools(mock_supports_function_calling: MagicMock):
    """Test generation of a response with tools."""
    mock_supports_function_calling.return_value = True
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, tell me about weather in San Francisco.")
    mock_llm_responses_with_tool(llm)
    output = await llm.generate(prompt, tools=[get_weather])
    assert output == [
        ToolCall(  # type: ignore
            arguments='{"location":"San Francisco"}',  # type: ignore
            name="get_weather",
            id="call_Dq3XWqfuMskh9SByzz5g00mM",
            type="function",
        )
    ]


@patch("litellm.supports_function_calling")
async def test_generation_with_tools_as_function_schemas(mock_supports_function_calling: MagicMock):
    """Test generation of a response with tools given as function schemas."""
    mock_supports_function_calling.return_value = True
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, tell me about weather in San Francisco.")
    mock_llm_responses_with_tool(llm)
    function_schema = convert_function_to_function_schema(get_weather)
    output = await llm.generate(prompt, tools=[function_schema])
    assert output == [
        ToolCall(  # type: ignore
            arguments='{"location":"San Francisco"}',  # type: ignore
            name="get_weather",
            id="call_Dq3XWqfuMskh9SByzz5g00mM",
            type="function",
        )
    ]


@patch("litellm.supports_function_calling")
async def test_generation_with_tools_no_tool_used(mock_supports_function_calling: MagicMock):
    """Test generation of a response with tools that are not used."""
    mock_supports_function_calling.return_value = True
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, how are you?")
    mock_llm_responses_with_tool_no_tool_used(llm)
    output = await llm.generate(prompt, tools=[get_weather])
    assert isinstance(output, str)
    assert output == "I'm fine."


@patch("litellm.supports_function_calling")
async def test_genration_with_tools_not_supported_in_model(mock_supports_function_calling: MagicMock):
    mock_supports_function_calling.return_value = False
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, how are you?")
    with pytest.raises(LLMNotSupportingToolUseError):
        await llm.generate(prompt, tools=[get_weather])


async def test_generation_with_static_prompt():
    """Test generation of a response with a static prompt."""

    class StaticPrompt(Prompt):
        """A static prompt."""

        user_prompt = "Hello, how are you?"

    llm = LiteLLM(api_key="test_key")
    prompt = StaticPrompt()
    options = LiteLLMOptions(mock_response="I'm fine, thank you.")
    output = await llm.generate(prompt, options=options)
    assert output == "I'm fine, thank you."


async def test_generation_with_static_prompt_with_parser():
    """Test generation of a response with a static prompt with a parser."""

    class StaticPromptWithParser(Prompt[None, int]):
        """A static prompt."""

        user_prompt = "Hello, how are you?"

    llm = LiteLLM(api_key="test_key")
    prompt = StaticPromptWithParser()
    options = LiteLLMOptions(mock_response="42")
    output = await llm.generate(prompt, options=options)
    assert output == 42
    raw_output = await llm.generate_raw(prompt, options=options)
    assert raw_output["response"] == "42"


async def test_generation_with_pydantic_output():
    """Test generation of a response with a Pydantic output."""

    class OutputModel(BaseModel):
        """Output model for the prompt."""

        response: str
        happiness: int

    class PydanticPrompt(Prompt[None, OutputModel]):
        """A Pydantic prompt."""

        user_prompt = "Hello, how are you?"

    llm = LiteLLM(api_key="test_key")
    prompt = PydanticPrompt()
    options = LiteLLMOptions(mock_response='{"response": "I\'m fine, thank you.", "happiness": 100}')
    output = await llm.generate(prompt, options=options)
    assert output.response == "I'm fine, thank you."  # type: ignore
    assert output.happiness == 100  # type: ignore


async def test_generation_with_metadata():
    """Test generation of a response."""
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, how are you?")
    options = LiteLLMOptions(mock_response="I'm fine, thank you.")
    output = await llm.generate_with_metadata(prompt, options=options)
    assert output.content == "I'm fine, thank you."
    assert output.metadata == {
        "completion_tokens": 20,
        "prompt_tokens": 10,
        "total_tokens": 30,
    }


@patch("litellm.supports_function_calling")
async def test_generation_with_metadata_and_tools(mock_supports_function_calling: MagicMock):
    """Test generation of a response with metadata and tools."""
    mock_supports_function_calling.return_value = True
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, tell me about weather in San Francisco.")
    mock_llm_responses_with_tool(llm)
    output = await llm.generate_with_metadata(prompt, tools=[get_weather])
    assert output.tool_calls == [  # type: ignore
        ToolCall(  # type: ignore
            arguments='{"location":"San Francisco"}',  # type: ignore
            name="get_weather",
            id="call_Dq3XWqfuMskh9SByzz5g00mM",
            type="function",
        )
    ]
    assert output.metadata == {
        "completion_tokens": 10,
        "prompt_tokens": 20,
        "total_tokens": 30,
    }


@patch("litellm.supports_function_calling")
async def test_generation_with_metadata_and_tools_no_tool_used(mock_supports_function_calling: MagicMock):
    """Test generation of a response with tools that are not used."""
    mock_supports_function_calling.return_value = True
    llm = LiteLLM(api_key="test_key")
    prompt = MockPrompt("Hello, how are you?")
    mock_llm_responses_with_tool_no_tool_used(llm)
    output = await llm.generate_with_metadata(prompt, tools=[get_weather])
    assert output.content == "I'm fine."
    assert output.metadata == {
        "completion_tokens": 10,
        "prompt_tokens": 20,
        "total_tokens": 30,
    }


async def test_generation_without_image_support():
    """Test generation of a response without image support."""
    llm = LiteLLM(api_key="test_key")
    prompt = MockPromptWithImage("Hello, what is on this image?")
    with pytest.raises(LLMNotSupportingImagesError):
        await llm.generate(prompt)


async def test_pickling():
    """Test pickling of the LiteLLM class."""
    llm = LiteLLM(
        model_name="gpt-3.5-turbo",
        default_options=LiteLLMOptions(mock_response="I'm fine, thank you."),
        custom_model_cost_config={
            "gpt-3.5-turbo": {
                "support_vision": True,
            }
        },
        use_structured_output=True,
        router=Router(),
        base_url="https://api.litellm.ai",
        api_key="test_key",
        api_version="v1",
    )
    llm_pickled = pickle.loads(pickle.dumps(llm))  # noqa: S301
    assert llm_pickled.model_name == "gpt-3.5-turbo"
    assert llm_pickled.default_options.mock_response == "I'm fine, thank you."
    assert llm_pickled.custom_model_cost_config == {
        "gpt-3.5-turbo": {
            "support_vision": True,
        }
    }
    assert llm_pickled.use_structured_output
    assert llm_pickled.router.model_list == []
    assert llm_pickled.base_url == "https://api.litellm.ai"
    assert llm_pickled.api_key == "test_key"
    assert llm_pickled.api_version == "v1"


async def test_init_registers_model_with_custom_cost_config():
    """Test that custom model cost config properly registers the model with LiteLLM."""
    custom_config = {
        "some_model": {
            "support_vision": True,
            "input_cost_per_token": 0.0015,
            "output_cost_per_token": 0.002,
            "max_tokens": 4096,
        }
    }

    with patch("litellm.register_model") as mock_register:
        # Create LLM instance with custom config
        LiteLLM(
            model_name="some_model",
            custom_model_cost_config=custom_config,
        )

        # Verify register_model was called with the correct config
        mock_register.assert_called_once_with(custom_config)


async def test_init_does_not_register_model_if_no_cost_config_is_provided():
    """Test that the model is not registered if no cost config is provided."""
    with patch("litellm.register_model") as mock_register:
        LiteLLM(
            model_name="some_model",
        )
        mock_register.assert_not_called()


async def test_pickling_registers_model_with_custom_cost_config():
    """Test that the model is registered with LiteLLM when unpickled."""
    custom_config = {
        "some_model": {
            "support_vision": True,
            "input_cost_per_token": 0.0015,
            "output_cost_per_token": 0.002,
            "max_tokens": 4096,
        }
    }
    llm = LiteLLM(
        model_name="some_model",
        custom_model_cost_config=custom_config,
    )
    with patch("litellm.register_model") as mock_register:
        llm_pickled = pickle.loads(pickle.dumps(llm))  # noqa: S301
        assert llm_pickled.custom_model_cost_config == custom_config
        mock_register.assert_called_once_with(custom_config)


def test_get_token_id():
    """Test that token id lookup"""
    llm = LiteLLM(model_name="gpt-4o")
    token_id = llm.get_token_id("Yes")
    assert token_id == 13022
