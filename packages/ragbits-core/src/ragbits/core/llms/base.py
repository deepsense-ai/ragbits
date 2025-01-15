import enum
import warnings as wrngs
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, ClassVar, Generic, TypeVar, cast, overload

from pydantic import BaseModel

from ragbits.core import llms
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, ChatFormat, OutputT
from ragbits.core.utils.config_handling import ConfigurableComponent

LLMClientOptionsT = TypeVar("LLMClientOptionsT", bound=Options)


class LLMType(enum.Enum):
    """
    Types of LLMs based on supported features
    """

    TEXT = "text"
    VISION = "vision"
    STRUCTURED_OUTPUT = "structured_output"


class LLMResponseWithMetadata(BaseModel, Generic[OutputT]):
    """
    A schema of output with metadata
    """
    llm_result: OutputT
    metadata: dict[str, Any]


class LLM(ConfigurableComponent[LLMClientOptionsT], ABC):
    """
    Abstract class for interaction with Large Language Model.
    """

    options_cls: type[LLMClientOptionsT]
    default_module: ClassVar = llms
    configuration_key: ClassVar = "llm"

    def __init__(self, model_name: str, default_options: LLMClientOptionsT | None = None) -> None:
        """
        Constructs a new LLM instance.

        Args:
            model_name: Name of the model to be used.
            default_options: Default options to be used.

        Raises:
            TypeError: If the subclass is missing the 'options_cls' attribute.
        """
        super().__init__(default_options=default_options)
        self.model_name = model_name

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "options_cls"):
            raise TypeError(f"Class {cls.__name__} is missing the 'options_cls' attribute")

    def count_tokens(self, prompt: BasePrompt) -> int:  # noqa: PLR6301
        """
        Counts tokens in the prompt.

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
        options: LLMClientOptionsT | None = None,
    ) -> dict[str, Any]:
        """
        Prepares and sends a prompt to the LLM and returns the raw response (without parsing).

        Args:
            prompt: Formatted prompt template with conversation.
            options: Options to use for the LLM client.

        Returns:
            Raw response from LLM.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        response = await self._call(
            conversation=self._format_chat_for_llm(prompt),
            options=merged_options,
            json_mode=prompt.json_mode,
            output_schema=prompt.output_schema(),
        )

        return response

    @overload
    async def generate(
        self,
        prompt: BasePromptWithParser[OutputT],
        *,
        options: LLMClientOptionsT | None = None,
    ) -> OutputT: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> OutputT: ...

    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> OutputT:
        """
        Prepares and sends a prompt to the LLM and returns response parsed to the
        output type of the prompt (if available).

        Args:
            prompt: Formatted prompt template with conversation and optional response parsing configuration.
            options: Options to use for the LLM client.

        Returns:
            Text response from LLM.
        """
        response = await self.generate_raw(prompt, options=options)
        return cast(OutputT, self._format_raw_llm_response(llm_response=response, prompt=prompt))

    async def generate_with_metadata(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[Any]:
        """
        Prepares and sends a prompt to the LLM and returns response parsed to the
        output type of the prompt (if available).

        Args:
            prompt: Formatted prompt template with conversation and optional response parsing configuration.
            options: Options to use for the LLM client.

        Returns:
            Text response from LLM.
        """
        response = await self.generate_raw(prompt, options=options)
        llm_result = self._format_raw_llm_response(llm_response=response, prompt=prompt)
        return LLMResponseWithMetadata(llm_result=llm_result, metadata=response)

    async def generate_streaming(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Prepares and sends a prompt to the LLM and streams the results.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Options to use for the LLM client.

        Returns:
            Response stream from LLM.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        response = await self._call_streaming(
            conversation=self._format_chat_for_llm(prompt),
            options=merged_options,
            json_mode=prompt.json_mode,
            output_schema=prompt.output_schema(),
        )
        async for text_piece in response:
            yield text_piece

    def _format_chat_for_llm(self, prompt: BasePrompt) -> ChatFormat:
        if prompt.list_images():
            wrngs.warn(message=f"Image input not implemented for {self.__class__.__name__}")
        return prompt.chat

    @staticmethod
    def _format_raw_llm_response(llm_response: dict[str, Any], prompt: BasePrompt) -> Any: # noqa: ANN401
        response_str = llm_response.pop("response")
        if isinstance(prompt, BasePromptWithParser):
            return prompt.parse_response(response_str)
        return response_str

    @abstractmethod
    async def _call(
        self,
        conversation: ChatFormat,
        options: LLMClientOptionsT,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict[str, Any]:
        """
        Calls LLM inference API.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).

        Returns:
            Response dict from LLM.
        """

    @abstractmethod
    async def _call_streaming(
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
