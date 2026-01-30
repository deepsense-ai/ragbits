import enum
import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Callable, MutableSequence
from typing import ClassVar, Generic, Literal, TypeVar, Union, cast, overload

from pydantic import BaseModel, Field, field_validator
from typing_extensions import deprecated

from ragbits.core import llms
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.audit.traces import trace
from ragbits.core.options import Options
from ragbits.core.prompt.base import (
    BasePrompt,
    BasePromptWithParser,
    ChatFormat,
    PromptOutputT,
    SimplePrompt,
)
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent
from ragbits.core.utils.function_schema import convert_function_to_function_schema


class LLMOptions(Options):
    """
    Options for the LLM.
    """

    max_tokens: int | None | NotGiven = NOT_GIVEN
    """The maximum number of tokens the LLM can use, if None, LLM will run forever"""


LLMClientOptionsT = TypeVar("LLMClientOptionsT", bound=LLMOptions)
Tool = Callable | dict
ToolChoiceWithCallable = Literal["none", "auto", "required"] | Tool
ToolChoice = Literal["none", "auto", "required"] | dict


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
        parsed_arguments = json.loads(tool_arguments)
        return parsed_arguments


class UsageItem(BaseModel):
    """
    A schema of token usage data
    """

    model: str

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    estimated_cost: float


class Usage(BaseModel):
    """
    A schema of token usage data
    """

    requests: list[UsageItem] = Field(default_factory=list)

    @classmethod
    def new(
        cls,
        llm: "LLM",
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> "Usage":
        """
        Creates a new Usage object.

        Args:
            llm: The LLM instance.
            prompt_tokens: The number of tokens in the prompt.
            completion_tokens: The number of tokens in the completion.
            total_tokens: The total number of tokens.
        """
        return cls(
            requests=[
                UsageItem(
                    model=llm.get_model_id(),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=llm.get_estimated_cost(prompt_tokens, completion_tokens),
                )
            ]
        )

    @property
    def n_requests(self) -> int:
        """
        Returns the number of requests.
        """
        return len(self.requests)

    @property
    def estimated_cost(self) -> float:
        """
        Returns the estimated cost.
        """
        return sum(request.estimated_cost for request in self.requests)

    @property
    def prompt_tokens(self) -> int:
        """
        Returns the number of prompt tokens.
        """
        return sum(request.prompt_tokens for request in self.requests)

    @property
    def completion_tokens(self) -> int:
        """
        Returns the number of completion tokens.
        """
        return sum(request.completion_tokens for request in self.requests)

    @property
    def total_tokens(self) -> int:
        """
        Returns the total number of tokens.
        """
        return sum(request.total_tokens for request in self.requests)

    @property
    def model_breakdown(self) -> dict[str, "Usage"]:
        """
        Returns the model breakdown.
        """
        breakdown = {}
        for request in self.requests:
            if request.model not in breakdown:
                breakdown[request.model] = Usage(requests=[request])
            else:
                breakdown[request.model] += request

        return breakdown

    def __add__(self, other: Union["Usage", "UsageItem"]) -> "Usage":
        if isinstance(other, Usage):
            return Usage(
                requests=self.requests + other.requests,
            )

        if isinstance(other, UsageItem):
            return Usage(requests=self.requests + [other])

        return NotImplemented

    def __iadd__(self, other: Union["Usage", "UsageItem"]) -> "Usage":
        if isinstance(other, Usage):
            self.requests += other.requests
            return self

        if isinstance(other, UsageItem):
            self.requests.append(other)
            return self

        return NotImplemented

    def __repr__(self) -> str:
        return (
            f"Usage(n_requests={self.n_requests}, "
            f"prompt_tokens={self.prompt_tokens}, "
            f"completion_tokens={self.completion_tokens}, "
            f"total_tokens={self.total_tokens}, "
            f"estimated_cost={self.estimated_cost})"
        )


class Reasoning(str):
    """A class for reasoning streaming"""


class LLMResponseWithMetadata(BaseModel, Generic[PromptOutputT]):
    """
    A schema of output with metadata
    """

    content: PromptOutputT
    metadata: dict = {}
    reasoning: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: Usage | None = None


T = TypeVar("T")


class LLMResultStreaming(AsyncIterator[T]):
    """
    An async iterator that will collect all yielded items by LLM.generate_streaming(). This object is returned
    by `run_streaming`. It can be used in an `async for` loop to process items as they arrive. After the loop completes,
    metadata is available as `metadata` attribute.
    """

    def __init__(self, generator: AsyncGenerator[T | LLMResponseWithMetadata]):
        self._generator = generator
        self.usage = Usage()

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        try:
            item = await self._generator.__anext__()
            match item:
                case str():
                    pass
                case ToolCall():
                    pass
                case LLMResponseWithMetadata():
                    self.metadata: LLMResponseWithMetadata = item
                    if item.usage:
                        self.usage += item.usage
                    # Exhaust generator to let trace context managers close properly
                    async for _ in self._generator:
                        pass
                    raise StopAsyncIteration
                case Usage():
                    self.usage += item
                case _:
                    raise ValueError(f"Unexpected item: {item}")
            return cast(T, item)
        except StopAsyncIteration:
            raise


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

    @abstractmethod
    def get_model_id(self) -> str:
        """
        Returns the model id.
        """

    @abstractmethod
    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Returns the estimated cost of the LLM call.

        Args:
            prompt_tokens: The number of tokens in the prompt.
            completion_tokens: The number of tokens in the completion.

        Returns:
            The estimated cost of the LLM call.
        """

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

        response = (
            await self._call(
                prompt=[prompt],
                options=merged_options,
            )
        )[0]

        returned = {
            "response": response["response"],
            "throughput": response["throughput"],
        }
        for opt in ["tool_calls", "usage"]:
            if opt in response:
                returned[opt] = response[opt]

        return returned

    @overload
    async def generate(
        self,
        prompt: BasePromptWithParser[PromptOutputT],
        *,
        tools: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: None = None,
        tool_choice: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: MutableSequence[BasePrompt | BasePromptWithParser[PromptOutputT]],
        *,
        tools: None = None,
        tool_choice: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> list[PromptOutputT]: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: list[Tool],
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> PromptOutputT | list[ToolCall]: ...

    @overload
    async def generate(
        self,
        prompt: MutableSequence[BasePrompt | BasePromptWithParser[PromptOutputT]],
        *,
        tools: list[Tool],
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> list[PromptOutputT | list[ToolCall]]: ...

    @overload
    async def generate(
        self,
        prompt: str | ChatFormat,
        *,
        tools: None = None,
        tool_choice: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> str: ...

    @overload
    async def generate(
        self,
        prompt: MutableSequence[str | ChatFormat],
        *,
        tools: None = None,
        tool_choice: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> list[str]: ...

    @overload
    async def generate(
        self,
        prompt: str | ChatFormat,
        *,
        tools: list[Tool],
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> str | list[ToolCall]: ...

    @overload
    async def generate(
        self,
        prompt: MutableSequence[str | ChatFormat],
        *,
        tools: list[Tool],
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> list[str | list[ToolCall]]: ...

    async def generate(
        self,
        prompt: str
        | ChatFormat
        | BasePrompt
        | BasePromptWithParser[PromptOutputT]
        | MutableSequence[ChatFormat | str]
        | MutableSequence[BasePrompt | BasePromptWithParser[PromptOutputT]],
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> str | PromptOutputT | list[ToolCall] | list[list[ToolCall] | str] | list[str | PromptOutputT | list[ToolCall]]:
        """
        Prepares and sends a prompt to the LLM and returns the parsed response.

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
                - Iterable of any of the above (MutableSequence is only for typing purposes)
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools
                - Callable: one of provided tools
            options: Options to use for the LLM client.

        Returns:
            Parsed response(s) from LLM or list of tool calls.
        """
        response = await self.generate_with_metadata(prompt, tools=tools, tool_choice=tool_choice, options=options)
        if isinstance(response, list):
            return [r.tool_calls if tools and r.tool_calls else r.content for r in response]
        else:
            return response.tool_calls if tools and response.tool_calls else response.content

    @overload
    async def generate_with_metadata(
        self,
        prompt: BasePrompt | BasePromptWithParser[PromptOutputT],
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[PromptOutputT]: ...

    @overload
    async def generate_with_metadata(
        self,
        prompt: MutableSequence[BasePrompt | BasePromptWithParser[PromptOutputT]],
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> list[LLMResponseWithMetadata[PromptOutputT]]: ...

    @overload
    async def generate_with_metadata(
        self,
        prompt: str | ChatFormat,
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResponseWithMetadata[str]: ...

    @overload
    async def generate_with_metadata(
        self,
        prompt: MutableSequence[str | ChatFormat],
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> list[LLMResponseWithMetadata[str]]: ...

    async def generate_with_metadata(
        self,
        prompt: str
        | ChatFormat
        | MutableSequence[str | ChatFormat]
        | BasePrompt
        | BasePromptWithParser[PromptOutputT]
        | MutableSequence[BasePrompt | BasePromptWithParser[PromptOutputT]],
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> (
        LLMResponseWithMetadata[str]
        | list[LLMResponseWithMetadata[str]]
        | LLMResponseWithMetadata[PromptOutputT]
        | list[LLMResponseWithMetadata[PromptOutputT]]
    ):
        """
        Prepares and sends a prompt to the LLM and returns response parsed to the
        output type of the prompt (if available).

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
                - Iterable of any of the above (MutableSequence is only for typing purposes)
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools
                - Callable: one of provided tools
            options: Options to use for the LLM client.

        Returns:
            ResponseWithMetadata object(s) with text response, list of tool calls and metadata information.
        """
        single_prompt = False
        if isinstance(prompt, BasePrompt | str) or isinstance(prompt[0], dict):
            single_prompt = True
            prompt = [prompt]  # type: ignore

        parsed_tools = (
            [convert_function_to_function_schema(tool) if callable(tool) else tool for tool in tools] if tools else None
        )
        parsed_tool_choice = convert_function_to_function_schema(tool_choice) if callable(tool_choice) else tool_choice

        prompts: list[BasePrompt] = [SimplePrompt(p) if isinstance(p, str | list) else p for p in prompt]  # type: ignore

        merged_options = (self.default_options | options) if options else self.default_options

        with trace(name="generate", model_name=self.model_name, prompt=prompts, options=repr(options)) as outputs:
            results = await self._call(
                prompt=prompts,
                options=merged_options,
                tools=parsed_tools,
                tool_choice=parsed_tool_choice,
            )

            parsed_responses = []
            for prompt, response in zip(prompts, results, strict=True):
                tool_calls = (
                    [ToolCall.model_validate(tool_call) for tool_call in _tool_calls]
                    if (_tool_calls := response.pop("tool_calls", None)) and tools
                    else None
                )

                usage = None
                if usage_data := response.pop("usage", None):
                    usage = Usage.new(
                        llm=self,
                        prompt_tokens=cast(int, usage_data.get("prompt_tokens")),
                        completion_tokens=cast(int, usage_data.get("completion_tokens")),
                        total_tokens=cast(int, usage_data.get("total_tokens")),
                    )

                content = response.pop("response")
                reasoning = response.pop("reasoning", None)

                if isinstance(prompt, BasePromptWithParser) and content:
                    content = await prompt.parse_response(content)

                response_with_metadata = LLMResponseWithMetadata[type(content)](  # type: ignore
                    content=content,
                    reasoning=reasoning,
                    tool_calls=tool_calls,
                    metadata=response,
                    usage=usage,
                )
                parsed_responses.append(response_with_metadata)
            outputs.response = parsed_responses

            prompt_tokens = sum(r.usage.prompt_tokens for r in parsed_responses if r.usage)
            outputs.prompt_tokens_batch = prompt_tokens
            record_metric(
                metric=LLMMetric.INPUT_TOKENS,
                value=prompt_tokens,
                metric_type=MetricType.HISTOGRAM,
                model=self.model_name,
            )

            total_throughput = sum(r["throughput"] for r in results if "throughput" in r)
            outputs.throughput_batch = total_throughput
            record_metric(
                metric=LLMMetric.PROMPT_THROUGHPUT,
                value=total_throughput,
                metric_type=MetricType.HISTOGRAM,
                model=self.model_name,
            )

            total_tokens = sum(r.usage.total_tokens for r in parsed_responses if r.usage)
            outputs.total_tokens_batch = total_tokens
            record_metric(
                metric=LLMMetric.TOKEN_THROUGHPUT,
                value=total_tokens / total_throughput,
                metric_type=MetricType.HISTOGRAM,
                model=self.model_name,
            )

        if single_prompt:
            return parsed_responses[0]

        return parsed_responses

    @overload
    def generate_streaming(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: None = None,
        tool_choice: None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResultStreaming[str | Reasoning]: ...

    @overload
    def generate_streaming(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: list[Tool],
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResultStreaming[str | Reasoning | ToolCall]: ...

    def generate_streaming(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> LLMResultStreaming:
        """
        This method returns an `LLMResultStreaming` object that can be asynchronously
        iterated over. After the loop completes, metadata is available as `metadata` attribute.

        Args:
            prompt: Formatted prompt template with conversation.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools
                - Callable: one of provided tools
            options: Options to use for the LLM.

        Returns:
            Response stream from LLM or list of tool calls.
        """
        return LLMResultStreaming(self._stream_internal(prompt, tools=tools, tool_choice=tool_choice, options=options))

    async def _stream_internal(
        self,
        prompt: str | ChatFormat | BasePrompt,
        *,
        tools: list[Tool] | None = None,
        tool_choice: ToolChoiceWithCallable | None = None,
        options: LLMClientOptionsT | None = None,
    ) -> AsyncGenerator[str | Reasoning | ToolCall | LLMResponseWithMetadata, None]:
        with trace(model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            merged_options = (self.default_options | options) if options else self.default_options
            if isinstance(prompt, str | list):
                prompt = SimplePrompt(prompt)

            parsed_tools = (
                [convert_function_to_function_schema(tool) if callable(tool) else tool for tool in tools]
                if tools
                else None
            )
            parsed_tool_choice = (
                convert_function_to_function_schema(tool_choice) if callable(tool_choice) else tool_choice
            )
            response = await self._call_streaming(
                prompt=prompt,
                options=merged_options,
                tools=parsed_tools,
                tool_choice=parsed_tool_choice,
            )

            content = ""
            reasoning = ""
            tool_calls = []
            usage_data = {}
            async for chunk in response:
                if text := chunk.get("response"):
                    if chunk.get("reasoning"):
                        reasoning += text
                        yield Reasoning(text)
                    else:
                        content += text
                        yield text

                if tools and (_tool_calls := chunk.get("tool_calls")):
                    for tool_call in _tool_calls:
                        parsed_tool_call = ToolCall.model_validate(tool_call)
                        tool_calls.append(parsed_tool_call)
                        yield parsed_tool_call

                if usage_chunk := chunk.get("usage"):
                    usage_data = usage_chunk

            usage = None
            if usage_data:
                usage = Usage.new(
                    llm=self,
                    prompt_tokens=cast(int, usage_data.get("prompt_tokens")),
                    completion_tokens=cast(int, usage_data.get("completion_tokens")),
                    total_tokens=cast(int, usage_data.get("total_tokens")),
                )

            outputs.response = LLMResponseWithMetadata[type(content or None)](  # type: ignore
                content=content or None,
                reasoning=reasoning or None,
                tool_calls=tool_calls or None,
                usage=usage,
            )

            yield outputs.response

    @abstractmethod
    async def _call(
        self,
        prompt: MutableSequence[BasePrompt],
        options: LLMClientOptionsT,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Calls LLM inference API.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools

        Returns:
            Response dict from LLM.
        """

    @abstractmethod
    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: LLMClientOptionsT,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Calls LLM inference API with output streaming.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools

        Returns:
            Response dict stream from LLM.
        """
