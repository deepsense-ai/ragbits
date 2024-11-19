from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.prompt import ChatFormat

from ..types import NotGiven

LLMClientOptions = TypeVar("LLMClientOptions", bound="LLMOptions")


@dataclass
class LLMOptions(ABC):
    """
    A dataclass that represents all available LLM call options.
    """

    _not_given: ClassVar[Any] = None

    def __or__(self, other: "LLMOptions") -> "LLMOptions":
        """
        Merges two LLMOptions, prioritizing non-NOT_GIVEN values from the 'other' object.
        """
        self_dict = asdict(self)
        other_dict = asdict(other)

        updated_dict = {
            key: other_dict.get(key, self_dict[key])
            if not isinstance(other_dict.get(key), NotGiven)
            else self_dict[key]
            for key in self_dict
        }

        return self.__class__(**updated_dict)

    def dict(self) -> dict[str, Any]:
        """
        Creates a dictionary representation of the LLMOptions instance.
        If a value is None, it will be replaced with a provider-specific not-given sentinel.

        Returns:
            A dictionary representation of the LLMOptions instance.
        """
        options = asdict(self)
        return {
            key: self._not_given if value is None or isinstance(value, NotGiven) else value
            for key, value in options.items()
        }


class LLMClient(Generic[LLMClientOptions], ABC):
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
        options: LLMClientOptions,
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
        options: LLMClientOptions,
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
