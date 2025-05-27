import enum
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import ClassVar, Generic, TypeVar, cast, overload

from pydantic import BaseModel

from ragbits.core import llms
from ragbits.core.audit.traces import trace
from ragbits.core.options import Options
from ragbits.core.prompt.base import (
    BasePrompt,
    BasePromptWithParser,
    ChatFormat,
    PromptOutputT,
    SimplePrompt,
)
from ragbits.core.utils.config_handling import ConfigurableComponent

LLMClientOptionsT = TypeVar("LLMClientOptionsT", bound=Options)


class LLMType(enum.Enum):
    """
    Types of LLMs based on supported features
    """

    TEXT = "text"
    VISION = "vision"
    STRUCTURED_OUTPUT = "structured_output"


class LLMResponseWithMetadata(BaseModel, Generic[PromptOutputT]):
    """
    A schema of output with metadata
    """

    content: PromptOutputT
    metadata: dict


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

    def get_token_id(self, token: str) -> int:
        """
        Gets token id.

        Args:
            token: The token to encode.

        Returns:
            The id for the given token.
        """
        raise NotImplementedError("Token id lookup is not supported by this model")

    async def generate_raw(
        self,
        prompt: BasePrompt | str | ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> dict:
        """
        Prepares and sends a prompt to the LLM and returns the raw response (without parsing).

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
            options: Options to use for the LLM client.

        Returns:
            Raw response from LLM.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        if isinstance(prompt, str | list):
            prompt = SimplePrompt(prompt)

        return await self._call(
            prompt=prompt,
            options=merged_options,
            json_mode=prompt.json_mode,
            output_schema=prompt.output_schema(),
        )

    @overload
    async def generate(
        self,
        prompt: BasePromptWithParser[PromptOutputT],
        *,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: str,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> str: ...

    @overload
    async def generate(
        self,
        prompt: ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> str: ...

    async def generate(
        self,
        prompt: BasePrompt | str | ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT:
        """
        Prepares and sends a prompt to the LLM and returns the parsed response.

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
            options: Options to use for the LLM client.

        Returns:
            Parsed response from LLM.
        """
        with trace(model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            raw_response = await self.generate_raw(prompt, options=options)
            if isinstance(prompt, BasePromptWithParser):
                response = await prompt.parse_response(raw_response["response"])
            else:
                response = cast(PromptOutputT, raw_response["response"])
            raw_response["response"] = response
            outputs.response = raw_response

        return response

    @overload
    async def generate_with_metadata(
        self,
        prompt: BasePromptWithParser[PromptOutputT],
        *,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]: ...

    @overload
    async def generate_with_metadata(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]: ...

    @overload
    async def generate_with_metadata(
        self,
        prompt: str,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]: ...

    @overload
    @overload
    async def generate_with_metadata(
        self,
        prompt: ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]: ...

    async def generate_with_metadata(
        self,
        prompt: BasePrompt | str | ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]:
        """
        Prepares and sends a prompt to the LLM and returns response parsed to the
        output type of the prompt (if available).

        Args:
            prompt: Formatted prompt template with conversation and optional response parsing configuration.
            options: Options to use for the LLM client.

        Returns:
            Text response from LLM with metadata.
        """
        with trace(model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            response = await self.generate_raw(prompt, options=options)
            content = response.pop("response")
            if isinstance(prompt, BasePromptWithParser):
                content = await prompt.parse_response(content)
            outputs.response = LLMResponseWithMetadata[type(content)](  # type: ignore
                content=content,
                metadata=response,
            )
        return outputs.response

    async def generate_streaming(
        self,
        prompt: BasePrompt | str | ChatFormat,
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
        with trace(model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            merged_options = (self.default_options | options) if options else self.default_options

            if isinstance(prompt, str | list):
                prompt = SimplePrompt(prompt)

            response = await self._call_streaming(
                prompt=prompt,
                options=merged_options,
                json_mode=prompt.json_mode,
                output_schema=prompt.output_schema(),
            )
            outputs.response = ""
            async for text in response:
                outputs.response += text
                yield text

    @abstractmethod
    async def _call(
        self,
        prompt: BasePrompt,
        options: LLMClientOptionsT,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict:
        """
        Calls LLM inference API.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).

        Returns:
            Response dict from LLM.
        """

    @abstractmethod
    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: LLMClientOptionsT,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Calls LLM inference API with output streaming.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).

        Returns:
            Response stream from LLM.
        """
