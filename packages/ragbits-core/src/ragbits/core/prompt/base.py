from abc import ABCMeta, abstractmethod
from typing import Any, Generic

from pydantic import BaseModel
from typing_extensions import Self, TypeVar

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
            PromptOutputT_co: The parsed response.

        Raises:
            ResponseParsingError: If the response cannot be parsed.
        """


class SimplePrompt(BasePrompt):
    """
    A simple prompt class that can handle bare strings or chat format dictionaries.
    """

    def __init__(self, content: str | ChatFormat) -> None:
        self._conversation_history: list[dict[str, Any]] = (
            [{"role": "user", "content": content}] if isinstance(content, str) else content
        )

    @property
    def chat(self) -> ChatFormat:
        """
        Returns the conversation in the chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        return self._conversation_history

    def __repr__(self) -> str:
        return f"SimplePrompt(content={self._conversation_history})"

    def add_tool_use_message(
        self,
        tool_call_id: str,
        tool_name: str,
        tool_arguments: dict,
        tool_call_result: Any,  # noqa: ANN401
    ) -> Self:
        """
        Add tool call messages to the conversation history.

        Args:
            tool_call_id (str): The id of the tool call.
            tool_name (str): The name of the tool.
            tool_arguments (dict): The arguments of the tool.
            tool_call_result (any): The tool call result.

        Returns:
            The current prompt with updated conversation history.
        """
        self._conversation_history.extend(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": str(tool_arguments),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": str(tool_call_result),
                },
            ]
        )
        return self
