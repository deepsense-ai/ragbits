import re

import pytest

from ragbits.core.prompt import Prompt
from ragbits.core.prompt.parsers import ResponseParsingError

from .test_prompt import _PromptOutput


async def test_prompt_with_str_output():
    """Test a prompt with a string output."""

    class TestPrompt(Prompt[None, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert await prompt.parse_response("Hi") == "Hi"


async def test_prompt_with_int_output():
    """Test a prompt with an int output."""

    class TestPrompt(Prompt[None, int]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert await prompt.parse_response("1") == 1

    with pytest.raises(ResponseParsingError):
        await prompt.parse_response("a")


async def test_prompt_with_model_output():
    """Test a prompt with a model output."""

    class TestPrompt(Prompt[None, _PromptOutput]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert await prompt.parse_response('{"song_title": "Hello", "song_lyrics": "World"}') == _PromptOutput(
        song_title="Hello", song_lyrics="World"
    )

    with pytest.raises(ResponseParsingError):
        await prompt.parse_response('{"song_title": "Hello"}')


async def test_prompt_with_float_output():
    """Test a prompt with a float output."""

    class TestPrompt(Prompt[None, float]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert await prompt.parse_response("1.0") == 1.0

    with pytest.raises(ResponseParsingError):
        await prompt.parse_response("a")


async def test_prompt_with_bool_output():
    """Test a prompt with a bool output."""

    class TestPrompt(Prompt[None, bool]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert await prompt.parse_response("true") is True
    assert await prompt.parse_response("false") is False

    with pytest.raises(ResponseParsingError):
        await prompt.parse_response("a")


async def test_prompt_with_int_and_custom_parser():
    """Test a prompt with an int output and a custom parser."""

    class TestPrompt(Prompt[None, int]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

        @staticmethod
        def response_parser(response: str) -> int:
            """
            Parse the response from the LLM to an int.

            Args:
                response (str): The response from the LLM.

            Returns:
                int: The parsed response.

            Raises:
                ResponseParsingError: If the response cannot be parsed.
            """
            match = re.search(r"\d+", response)
            if match:
                return int(match.group())
            raise ResponseParsingError("Could not parse response")

    prompt = TestPrompt()
    assert await prompt.parse_response("abcd k2") == 2

    with pytest.raises(ResponseParsingError):
        await prompt.parse_response("a")


def test_prompt_with_unknown_output_and_no_parser():
    """Test a prompt with an output type that doesn't have a default parser."""
    with pytest.raises(ValueError):

        class TestPrompt(Prompt[None, list]):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello"


async def test_prompt_with_unknown_output_and_custom_parser():
    """Test a prompt with an output type that doesn't have a default parser but has a custom parser."""

    class TestPrompt(Prompt[None, list]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

        @staticmethod
        def response_parser(response: str) -> list:
            """
            Parse the response from the LLM to a list.

            Args:
                response (str): The response from the LLM.

            Returns:
                list: The parsed response.

            Raises:
                ResponseParsingError: If the response cannot be parsed.
            """
            return response.split()

    prompt = TestPrompt()
    assert await prompt.parse_response("Hello World") == ["Hello", "World"]
    assert await prompt.parse_response("Hello") == ["Hello"]
