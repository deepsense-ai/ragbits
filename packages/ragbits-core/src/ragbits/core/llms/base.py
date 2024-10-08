from abc import ABC, abstractmethod
from functools import cached_property
from typing import Generic, cast, overload

from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, OutputT

from .clients.base import LLMClient, LLMClientOptions, LLMOptions


class LLM(Generic[LLMClientOptions], ABC):
    """Abstract class for interaction with Large Language Model.
    """

    _options_cls: type[LLMClientOptions]

    def __init__(self, model_name: str, default_options: LLMOptions | None = None) -> None:
        """Constructs a new LLM instance.

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
        """Client for the LLM.
        """

    def count_tokens(self, prompt: BasePrompt) -> int:
        """Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(len(message["content"]) for message in prompt.chat)

    async def generate_raw(
        self,
        prompt: BasePrompt,
        *,
        options: LLMOptions | None = None,
    ) -> str:
        """Prepares and sends a prompt to the LLM and returns the raw response (without parsing).

        Args:
            prompt: Formatted prompt template with conversation.
            options: Options to use for the LLM client.

        Returns:
            Raw text response from LLM.
        """
        options = (self.default_options | options) if options else self.default_options

        response = await self.client.call(
            conversation=prompt.chat,
            options=options,
            json_mode=prompt.json_mode,
            output_schema=prompt.output_schema(),
        )

        return response

    @overload
    async def generate(
        self,
        prompt: BasePromptWithParser[OutputT],
        *,
        options: LLMOptions | None = None,
    ) -> OutputT:
        ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMOptions | None = None,
    ) -> OutputT:
        ...

    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMOptions | None = None,
    ) -> OutputT:
        """Prepares and sends a prompt to the LLM and returns response parsed to the
        output type of the prompt (if available).

        Args:
            prompt: Formatted prompt template with conversation and optional response parsing configuration.
            options: Options to use for the LLM client.

        Returns:
            Text response from LLM.
        """
        response = await self.generate_raw(prompt, options=options)

        if isinstance(prompt, BasePromptWithParser):
            return prompt.parse_response(response)

        return cast(OutputT, response)
