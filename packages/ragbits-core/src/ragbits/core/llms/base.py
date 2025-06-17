import enum
import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from typing import ClassVar, Generic, TypeVar, overload

from pydantic import BaseModel, field_validator
from typing_extensions import deprecated

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
from ragbits.core.utils.function_schema import convert_function_to_function_schema

LLMClientOptionsT = TypeVar("LLMClientOptionsT", bound=Options)
Tool = Callable | dict


class LLMType(enum.Enum):
    """
    Types of LLMs based on supported features
    """

    TEXT = "text"
    VISION = "vision"
    STRUCTURED_OUTPUT = "structured_output"


class ToolCall(BaseModel):
    """
    A schema of tool call data
    """

    id: str
    type: str
    name: str
    arguments: dict

    @field_validator("arguments", mode="before")
    def parse_tool_arguments(cls, tool_arguments: str) -> dict:
        """
        Parser for converting tool arguments from string representation to dict
        """
        pased_arguments = json.loads(tool_arguments)
        return pased_arguments


class LLMResponseWithMetadata(BaseModel, Generic[PromptOutputT]):
    """
    A schema of output with metadata
    """

    content: PromptOutputT
    metadata: dict = {}
    tool_calls: list[ToolCall] | None = None


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

    @deprecated("Use generate_with_metadata() instead")
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
        prompt: str | ChatFormat,
        *,
        tools: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> str: ...

    @overload
    async def generate(
        self,
        prompt: str | ChatFormat,
        *,
        tools: list[Tool],
        options: LLMClientOptionsT | None = None,
    ) -> str | list[ToolCall]: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: list[Tool],
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT | list[ToolCall]: ...

    async def generate(
        self,
        prompt: str | ChatFormat | BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: list[Tool] | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> str | PromptOutputT | list[ToolCall]:
        """
        Prepares and sends a prompt to the LLM and returns the parsed response.

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
            tools: Functions to be used as tools by the LLM.
            options: Options to use for the LLM client.

        Returns:
            Parsed response from LLM or list of tool calls.
        """
        response = await self.generate_with_metadata(prompt, tools=tools, options=options)
        return response.tool_calls if tools and response.tool_calls else response.content

    @overload
    async def generate_with_metadata(
        self,
        prompt: str | ChatFormat,
        *,
        tools: list[Tool] | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[str]: ...

    @overload
    async def generate_with_metadata(
        self,
        prompt: BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: list[Tool] | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]: ...

    async def generate_with_metadata(
        self,
        prompt: str | ChatFormat | BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: list[Tool] | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[str] | LLMResponseWithMetadata[PromptOutputT]:
        """
        Prepares and sends a prompt to the LLM and returns response parsed to the
        output type of the prompt (if available).

        Args:
            prompt: Formatted prompt template with conversation and optional response parsing configuration.
            tools: Functions to be used as tools by the LLM.
            options: Options to use for the LLM client.

        Returns:
            Text response from LLM with metadata and list of tool calls.
        """
        with trace(name="generate", model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            merged_options = (self.default_options | options) if options else self.default_options

            if isinstance(prompt, str | list):
                prompt = SimplePrompt(prompt)

            parsed_tools = (
                [convert_function_to_function_schema(tool) if callable(tool) else tool for tool in tools]
                if tools
                else None
            )
            response = await self._call(
                prompt=prompt,
                options=merged_options,
                json_mode=prompt.json_mode,
                output_schema=prompt.output_schema(),
                tools=parsed_tools,
            )

            tool_calls = (
                [ToolCall.model_validate(tool_call) for tool_call in _tool_calls]
                if (_tool_calls := response.pop("tool_calls", None)) and tools
                else None
            )
            content = response.pop("response", None)
            if isinstance(prompt, BasePromptWithParser) and content:
                content = await prompt.parse_response(content)

            outputs.response = LLMResponseWithMetadata[type(content)](  # type: ignore
                content=content,
                tool_calls=tool_calls,
                metadata=response,
            )
            return outputs.response

    @overload
    def generate_streaming(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> AsyncGenerator[str, None]: ...

    @overload
    def generate_streaming(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: list[Tool],
        options: LLMClientOptionsT | None = None,
    ) -> AsyncGenerator[str | ToolCall, None]: ...

    async def generate_streaming(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: list[Tool] | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> AsyncGenerator[str | ToolCall, None]:
        """
        Prepares and sends a prompt to the LLM and streams the results.

        Args:
            prompt: Formatted prompt template with conversation.
            tools: Functions to be used as tools by the LLM.
            options: Options to use for the LLM.

        Returns:
            Response stream from LLM or list of tool calls.
        """
        with trace(model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            merged_options = (self.default_options | options) if options else self.default_options

            if isinstance(prompt, str | list):
                prompt = SimplePrompt(prompt)

            parsed_tools = (
                [convert_function_to_function_schema(tool) if callable(tool) else tool for tool in tools]
                if tools
                else None
            )
            response = await self._call_streaming(
                prompt=prompt,
                options=merged_options,
                json_mode=prompt.json_mode,
                output_schema=prompt.output_schema(),
                tools=parsed_tools,
            )

            content = ""
            tool_calls = []
            async for chunk in response:
                if text := chunk.get("response"):
                    content += text
                    yield text

                if tools and (_tool_calls := chunk.get("tool_calls")):
                    for tool_call in _tool_calls:
                        parsed_tool_call = ToolCall.model_validate(tool_call)
                        tool_calls.append(parsed_tool_call)
                        yield parsed_tool_call

            outputs.response = LLMResponseWithMetadata[type(content or None)](  # type: ignore
                content=content or None,
                tool_calls=tool_calls or None,
            )

    @abstractmethod
    async def _call(
        self,
        prompt: BasePrompt,
        options: LLMClientOptionsT,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Calls LLM inference API.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).
            tools: Functions to be used as tools by the LLM.

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
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Calls LLM inference API with output streaming.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).
            tools: Functions to be used as tools by the LLM.

        Returns:
            Response dict stream from LLM.
        """
