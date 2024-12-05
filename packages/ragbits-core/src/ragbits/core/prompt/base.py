from abc import ABCMeta, abstractmethod
from typing import Any, Generic

from pydantic import BaseModel
from typing_extensions import TypeVar

ChatFormat = list[dict[str, Any]]
OutputT = TypeVar("OutputT", default=str)


class BasePrompt(metaclass=ABCMeta):
    """
    Base class for prompts.
    """

    @property
    @abstractmethod
    def chat(self) -> ChatFormat:
        """
        Returns the conversation in the standard OpenAI chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """

    @property
    def json_mode(self) -> bool:
        """
        Returns whether the prompt should be sent in JSON mode.
        """
        return self.output_schema() is not None

    def output_schema(self) -> dict | type[BaseModel] | None:  # noqa: PLR6301
        """
        Returns the schema of the desired output. Can be used to request structured output from the LLM API
        or to validate the output. Can return either a Pydantic model or a JSON schema.
        """
        return None

    # ruff: noqa
    def list_images(self) -> list[bytes | str]:
        """
        Returns the schema of the list of images compatible with LLM APIs
        Returns:
            list of dictionaries
        """
        return []


class BasePromptWithParser(Generic[OutputT], BasePrompt, metaclass=ABCMeta):
    """
    Base class for prompts that know how to parse the output from the LLM to their specific
    output type.
    """

    @abstractmethod
    def parse_response(self, response: str) -> OutputT:
        """
        Parse the response from the LLM to the desired output type.

        Args:
            response (str): The response from the LLM.

        Returns:
            OutputT: The parsed response.

        Raises:
            ResponseParsingError: If the response cannot be parsed.
        """
