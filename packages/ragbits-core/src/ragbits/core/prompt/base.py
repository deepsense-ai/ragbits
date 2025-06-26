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
    def chat(self) -> ChatFormat:
        """
        Returns the conversation in the standard OpenAI chat format.

        Returns:
            ChatFormat: A list of dictionaries, each containing the role and content of a message.
        """
        if not hasattr(self, "_conversation_history"):
            self._conversation_history: list[dict[str, Any]] = []
        return self._conversation_history

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

    def add_assistant_message(self, message: str | PromptOutputT) -> Self:
        """
        Add an assistant message to the conversation history.

        Args:
            message (str): The assistant message content.

        Returns:
            Prompt[PromptInputT, PromptOutputT]: The current prompt instance to allow chaining.
        """
        if not hasattr(self, "_conversation_history"):
            self._conversation_history = []

        if isinstance(message, BaseModel):
            message = message.model_dump_json()
        self._conversation_history.append({"role": "assistant", "content": str(message)})
        return self

    def add_tool_use_message(
        self,
        id: str,
        name: str,
        arguments: dict,
        result: Any,  # noqa: ANN401
    ) -> Self:
        """
        Add tool call messages to the conversation history.

        Args:
            id (str): The id of the tool call.
            name (str): The name of the tool.
            arguments (dict): The arguments of the tool.
            result (any): The tool call result.

        Returns:
            Prompt[PromptInputT, PromptOutputT]: The current prompt instance to allow chaining.
        """
        if not hasattr(self, "_conversation_history"):
            self._conversation_history = []

        self._conversation_history.extend(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": str(arguments),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": id,
                    "content": str(result),
                },
            ]
        )

        return self

    def add_user_message(self, message: str | dict[str, Any] | list[dict[str, Any]]) -> Self:
        """
        Add a user message to the conversation history.

        Args:
            message: The user message content. Can be:
                - A string: Used directly as content
                - A dictionary: With format {"type": "text", "text": "message"} or image content

        Returns:
            Prompt: The current prompt instance to allow chaining.
        """
        if not hasattr(self, "_conversation_history"):
            self._conversation_history = []

        self._conversation_history.append({"role": "user", "content": message})
        return self


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
        self._conversation_history: list[dict[str, Any]] = (
            [{"role": "user", "content": content}] if isinstance(content, str) else content
        )
