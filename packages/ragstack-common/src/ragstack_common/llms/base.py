from abc import ABC, abstractmethod
from functools import cached_property
from typing import Generic, Optional, Type

from ragstack_common.prompt import Prompt

from .clients.base import LLMClient, LLMClientOptions, LLMOptions


class LLM(Generic[LLMClientOptions], ABC):
    """
    Abstract class for interaction with Large Language Model.
    """

    _options_cls: Type[LLMClientOptions]

    def __init__(self, model_name: str, default_options: Optional[LLMOptions] = None) -> None:
        """
        Constructs a new LLM instance.

        Args:
            model_name: Name of the model to be used.
            default_options: Default options to be used.

        Raises:
            TypeError: If the subclass is missing the '_options_cls' attribute.
        """
        self.model_name = model_name
        self.default_options = default_options or self._options_cls()

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "_options_cls"):
            raise TypeError(f"Class {cls.__name__} is missing the '_options_cls' attribute")

    @cached_property
    @abstractmethod
    def client(self) -> LLMClient:
        """
        Client for the LLM.
        """

    def count_tokens(self, prompt: Prompt) -> int:
        """
        Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(len(message["content"]) for message in prompt.chat)

    async def generate_text(
        self,
        prompt: Prompt,
        *,
        options: Optional[LLMOptions] = None,
    ) -> str:
        """
        Prepares and sends a prompt to the LLM and returns the response.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.
            options: Options to use for the LLM client.

        Returns:
            Text response from LLM.
        """
        options = (self.default_options | options) if options else self.default_options

        response = await self.client.call(
            conversation=prompt.chat,
            options=options,
            json_mode=prompt.json_mode,
        )

        return response
