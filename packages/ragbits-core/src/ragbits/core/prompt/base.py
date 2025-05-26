from abc import ABCMeta, abstractmethod
from typing import Any, Generic

from pydantic import BaseModel
from typing_extensions import TypeVar

ChatFormat = list[dict[str, Any]]
PromptOutputT = TypeVar("PromptOutputT", default=str)


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

    def list_images(self) -> list[str]:  # noqa: PLR6301
        """
        Returns the images in form of URLs or base64 encoded strings.

        Returns:
            list of images
        """
        return []


class BasePromptWithParser(Generic[PromptOutputT], BasePrompt, metaclass=ABCMeta):
    """
    Base class for prompts that know how to parse the output from the LLM to their specific
    output type.
    """

    @abstractmethod
    async def parse_response(self, response: str) -> PromptOutputT:
        """
        Parse the response from the LLM to the desired output type.

        Args:
            response (str): The response from the LLM.

        Returns:
            PromptOutputT: The parsed response.

        Raises:
            ResponseParsingError: If the response cannot be parsed.
        """


class SimplePrompt(BasePrompt):
    """
    A simple prompt class that can handle bare strings or chat format dictionaries.
    """

    def __init__(self, content: str | ChatFormat) -> None:
        self._content = content

    @property
    def chat(self) -> ChatFormat:
        """
        Returns the conversation in the chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        if isinstance(self._content, str):
            return [{"role": "user", "content": self._content}]
        return self._content
