import contextlib
import enum
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable, Generator
from typing import (
    Any,
    ClassVar,
    Generic,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from griffe import Docstring, DocstringSectionKind
from pydantic import BaseModel, Field, create_model

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

Tools = list[Callable] | list[dict]


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


class ToolCall(BaseModel):
    """
    A schema of tool call data
    """

    tool_name: str
    tool_arguments: str
    tool_type: str
    tool_call_id: str


class ToolCallsResponse(BaseModel):
    """
    A schema of output with tool calls
    """

    tool_calls: list[ToolCall]


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
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Prepares and sends a prompt to the LLM and returns the raw response (without parsing).

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
            options: Options to use for the LLM client.
            tools: Functions to be used as tools by LLM.

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
            tools=tools,
        )

    @overload
    async def generate(
        self,
        prompt: BasePromptWithParser[PromptOutputT],
        *,
        options: LLMClientOptionsT | None = None,
        tools: None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: BasePromptWithParser[PromptOutputT],
        *,
        options: LLMClientOptionsT | None = None,
        tools: Tools | None = None,
    ) -> PromptOutputT | ToolCallsResponse: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
        tools: None = None,
    ) -> PromptOutputT: ...

    @overload
    async def generate(
        self,
        prompt: BasePrompt,
        *,
        options: LLMClientOptionsT | None = None,
        tools: Tools | None = None,
    ) -> PromptOutputT | ToolCallsResponse: ...

    @overload
    async def generate(
        self,
        prompt: str,
        *,
        options: LLMClientOptionsT | None = None,
        tools: None = None,
    ) -> str: ...

    @overload
    async def generate(
        self,
        prompt: str,
        *,
        options: LLMClientOptionsT | None = None,
        tools: Tools | None = None,
    ) -> str | ToolCallsResponse: ...

    @overload
    async def generate(
        self,
        prompt: ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
        tools: None = None,
    ) -> str: ...

    @overload
    async def generate(
        self,
        prompt: ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
        tools: Tools | None = None,
    ) -> str | ToolCallsResponse: ...

    async def generate(
        self,
        prompt: BasePrompt | str | ChatFormat,
        *,
        options: LLMClientOptionsT | None = None,
        tools: Tools | None = None,
    ) -> PromptOutputT | ToolCallsResponse:
        """
        Prepares and sends a prompt to the LLM and returns the parsed response.

        Args:
            prompt: Can be one of:
                - BasePrompt instance: Formatted prompt template with conversation
                - str: Simple text prompt that will be sent as a user message
                - ChatFormat: List of message dictionaries in OpenAI chat format
            options: Options to use for the LLM client.
            tools: Functions to be used as tools by LLM.

        Returns:
            Parsed response from LLM or list of tool calls.
        """
        with trace(model_name=self.model_name, prompt=prompt, options=repr(options)) as outputs:
            function_schemas: list[dict] | None
            if tools and callable(tools[0]):
                function_schemas = [self._convert_function_to_function_schema(cast(Callable, tool)) for tool in tools]
            else:
                function_schemas = cast(list[dict] | None, tools)

            raw_response = await self.generate_raw(prompt, options=options, tools=function_schemas)

            if tools:
                tool_call_dicts = raw_response["tool_calls"]
                if tool_call_dicts:
                    tool_calls = ToolCallsResponse(
                        tool_calls=[ToolCall.model_validate(tool_call_dict) for tool_call_dict in tool_call_dicts]
                    )
                    raw_response["tool_calls"] = tool_calls
                    outputs.response = raw_response
                    return tool_calls

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
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Calls LLM inference API.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Schema for structured response (either Pydantic model or a JSON schema).
            tools: Functions to be used as tools by LLM.

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

    # This function was copied with a few changes from openai-agents-python library
    # https://github.com/openai/openai-agents-python/blob/main/src/agents/function_schema.py
    @staticmethod
    def _generate_func_documentation(
        func: Callable[..., Any],
    ) -> dict:
        """
        Extracts metadata from a function docstring, in preparation for sending it to an LLM as a tool.

        Args:
            func: The function to extract documentation from.

        Returns:
            A dict containing the function's name, description, and parameter
            descriptions.
        """
        name = func.__name__
        doc = inspect.getdoc(func)
        if not doc:
            return {"name": name, "description": None, "param_descriptions": None}

        with LLM._suppress_griffe_logging():
            docstring = Docstring(doc, lineno=1, parser="google")
            parsed = docstring.parse()

        description: str | None = next(
            (section.value for section in parsed if section.kind == DocstringSectionKind.text), None
        )

        param_descriptions: dict[str, str] = {
            param.name: param.description
            for section in parsed
            if section.kind == DocstringSectionKind.parameters
            for param in section.value
        }

        return {
            "name": func.__name__,
            "description": description,
            "param_descriptions": param_descriptions or None,
        }

    # This function was copied with a few changes from openai-agents-python library
    # https://github.com/openai/openai-agents-python/blob/main/src/agents/function_schema.py
    @staticmethod
    @contextlib.contextmanager
    def _suppress_griffe_logging() -> Generator:
        # Suppresses warnings about missing annotations for params
        logger = logging.getLogger("griffe")
        previous_level = logger.getEffectiveLevel()
        logger.setLevel(logging.ERROR)
        try:
            yield
        finally:
            logger.setLevel(previous_level)

    # This function was copied with a few changes from openai-agents-python library
    # https://github.com/openai/openai-agents-python/blob/main/src/agents/function_schema.py
    @staticmethod
    def _convert_function_to_function_schema(
        func: Callable[..., Any],
    ) -> dict:
        """
        Given a python function, extracts a `FuncSchema` from it, capturing the name, description,
        parameter descriptions, and other metadata.

        Args:
            func: The function to extract the schema from.

        Returns:
            A dict containing the function's name, description, parameter descriptions,
            and other metadata.
        """
        # 1. Grab docstring info
        doc_info = LLM._generate_func_documentation(func)
        param_descs = doc_info["param_descriptions"] or {}

        func_name = doc_info["name"] if doc_info else func.__name__

        # 2. Inspect function signature and get type hints
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        params = list(sig.parameters.items())
        filtered_params = []

        if params:
            first_name, first_param = params[0]
            # Prefer the evaluated type hint if available
            ann = type_hints.get(first_name, first_param.annotation)
            filtered_params.append((first_name, first_param))

        # For parameters other than the first, raise error if any use RunContextWrapper.
        for name, param in params[1:]:
            ann = type_hints.get(name, param.annotation)
            filtered_params.append((name, param))

        # We will collect field definitions for create_model as a dict:
        #   field_name -> (type_annotation, default_value_or_Field(...))
        fields: dict[str, Any] = {}

        for name, param in filtered_params:
            ann = type_hints.get(name, param.annotation)
            default = param.default

            # If there's no type hint, assume `Any`
            if ann == inspect._empty:
                ann = Any

            # If a docstring param description exists, use it
            field_description = param_descs.get(name, None)

            # Handle different parameter kinds
            if param.kind == param.VAR_POSITIONAL:
                # e.g. *args: extend positional args
                if get_origin(ann) is tuple:
                    # e.g. def foo(*args: tuple[int, ...]) -> treat as List[int]
                    args_of_tuple = get_args(ann)
                    args_of_tuple_with_ellipsis_length = 2
                    ann = (
                        list[args_of_tuple[0]]  # type: ignore
                        if len(args_of_tuple) == args_of_tuple_with_ellipsis_length and args_of_tuple[1] is Ellipsis
                        else list[Any]
                    )
                else:
                    # If user wrote *args: int, treat as List[int]
                    ann = list[ann]  # type: ignore

                # Default factory to empty list
                fields[name] = (
                    ann,
                    Field(default_factory=list, description=field_description),  # type: ignore
                )

            elif param.kind == param.VAR_KEYWORD:
                # **kwargs handling
                if get_origin(ann) is dict:
                    # e.g. def foo(**kwargs: dict[str, int])
                    dict_args = get_args(ann)
                    dict_args_to_check_length = 2
                    ann = (
                        dict[dict_args[0], dict_args[1]]  # type: ignore
                        if len(dict_args) == dict_args_to_check_length
                        else dict[str, Any]
                    )  # type: ignore
                else:
                    # e.g. def foo(**kwargs: int) -> Dict[str, int]
                    ann = dict[str, ann]  # type: ignore

                fields[name] = (
                    ann,
                    Field(default_factory=dict, description=field_description),  # type: ignore
                )

            elif default == inspect._empty:
                # Required field
                fields[name] = (
                    ann,
                    Field(..., description=field_description),
                )
            else:
                # Parameter with a default value
                fields[name] = (
                    ann,
                    Field(default=default, description=field_description),
                )

        # 3. Dynamically build a Pydantic model
        dynamic_model = create_model(f"{func_name}_args", __base__=BaseModel, **fields)

        # 4. Build JSON schema from that model
        json_schema = dynamic_model.model_json_schema()

        return {
            "type": "function",
            "function": {
                "name": func_name,
                "description": doc_info["description"] if doc_info else None,
                "parameters": {
                    "type": "object",
                    "properties": json_schema["properties"],
                    "required": json_schema["required"],
                },
            },
        }
