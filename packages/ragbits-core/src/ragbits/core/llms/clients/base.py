from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.options import Options
from ragbits.core.prompt import ChatFormat

LLMClientOptionsT = TypeVar("LLMClientOptionsT", bound=Options)


class LLMClient(Generic[LLMClientOptionsT], ABC):
    """
    Abstract client for a direct communication with LLM.
    """

    def __init__(self, model_name: str) -> None:
        """
        Constructs a new LLMClient instance.

        Args:
            model_name: Name of the model to be used.
        """
        self.model_name = model_name

    @abstractmethod
    async def call(
        self,
        conversation: ChatFormat,
        options: LLMClientOptionsT,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> str:
        """
        Calls LLM inference API.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).

        Returns:
            Response string from LLM.
        """

    @abstractmethod
    async def call_streaming(
        self,
        conversation: ChatFormat,
        options: LLMClientOptionsT,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Calls LLM inference API with output streaming.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).

        Returns:
            Response stream from LLM.
        """
