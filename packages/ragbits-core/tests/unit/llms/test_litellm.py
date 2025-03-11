import pytest
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
    def parse_response(response: str) -> int:
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
