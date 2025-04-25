import pickle
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest
from litellm import Router
from pydantic import BaseModel

from ragbits.core.llms.exceptions import LLMNotSupportingImagesError
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.prompt import Prompt
from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, ChatFormat


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
    assert output.response == "I'm fine, thank you."
    assert output.happiness == 100


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


def test_get_yes_no_token_ids_with_tiktoken() -> None:
    test_model_name = "some_openai_model"
    llm = LiteLLM(model_name="some_openai_model")
    with patch("ragbits.core.llms.litellm.tiktoken") as mock_tiktoken:
        mock_encoder = MagicMock()
        mock_encoder.encode.side_effect = lambda token: [123] if token == " Yes" else [456]  # noqa: S105
        mock_tiktoken.encoding_for_model.return_value = mock_encoder
        token_ids = llm.get_yes_no_token_ids()
        assert token_ids == {123: 1, 456: 1}
        mock_tiktoken.encoding_for_model.assert_called_once_with(test_model_name)


def test_get_yes_no_token_ids_with_autotokenizer() -> None:
    """Test with HuggingFace model using AutoTokenizer"""
    test_model_name = "bert-base-uncased"
    llm = LiteLLM(model_name=test_model_name)

    with (
        patch("ragbits.core.llms.litellm.AutoTokenizer") as mock_autotokenizer,
        patch("ragbits.core.llms.litellm.tiktoken.encoding_for_model", side_effect=ValueError),
    ):
        # Setup mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda token: [1, 789] if token == " Yes" else [1, 987]  # noqa: S105
        mock_autotokenizer.from_pretrained.return_value = mock_tokenizer

        # Mock tiktoken to fail first
        # with patch("ragbits.core.llms.litellm.tiktoken.encoding_for_model", side_effect=ValueError):
        token_ids = llm.get_yes_no_token_ids()

        assert token_ids == {789: 1, 987: 1}
        mock_autotokenizer.from_pretrained.assert_called_once_with(test_model_name)


def test_get_yes_no_token_ids_no_tokenizer() -> None:
    test_model_name = "some_other_model"
    llm = LiteLLM(model_name=test_model_name)
    with (
        patch("ragbits.core.llms.litellm.AutoTokenizer", side_effect=HTTPError),
        patch("ragbits.core.llms.litellm.tiktoken.encoding_for_model", side_effect=ValueError),
    ):
        token_ids = llm.get_yes_no_token_ids()
        assert token_ids is None
