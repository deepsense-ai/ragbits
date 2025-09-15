import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from inspect import iscoroutinefunction
from types import ModuleType, SimpleNamespace
from typing import ClassVar, Generic, cast, overload

from pydantic import BaseModel, Field

from ragbits import agents
from ragbits.agents.exceptions import (
    AgentInvalidPostProcessorError,
    AgentInvalidPromptInputError,
    AgentMaxTokensExceededError,
    AgentMaxTurnsExceededError,
    AgentNextPromptOverLimitError,
    AgentToolDuplicateError,
    AgentToolExecutionError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.agents.mcp.server import MCPServer
from ragbits.agents.mcp.utils import get_tools
from ragbits.agents.post_processors.base import BasePostProcessor
from ragbits.agents.tool import Tool, ToolCallResult
from ragbits.core.audit.traces import trace
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata, ToolCall, Usage
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePrompt, ChatFormat, SimplePrompt
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill


@dataclass
class AgentResult(Generic[PromptOutputT]):
    """
    Result of the agent run.
    """

    content: PromptOutputT
    """The output content of the agent."""
    metadata: dict
    """The additional data returned by the agent."""
    history: ChatFormat
    """The history of the agent."""
    tool_calls: list[ToolCallResult] | None = None
    """Tool calls run by the agent."""
    usage: Usage = Field(default_factory=Usage)
    """The token usage of the agent run."""


class AgentOptions(Options, Generic[LLMClientOptionsT]):
    """
    Options for the agent run.
    """

    llm_options: LLMClientOptionsT | None | NotGiven = NOT_GIVEN
    """The options for the LLM."""
    max_turns: int | None | NotGiven = NOT_GIVEN
    """The maximum number of turns the agent can take, if NOT_GIVEN,
    it defaults to 10, if None, agent will run forever"""
    max_total_tokens: int | None | NotGiven = NOT_GIVEN
    """The maximum number of tokens the agent can use, if NOT_GIVEN
    or None, agent will run forever"""
    max_prompt_tokens: int | None | NotGiven = NOT_GIVEN
    """The maximum number of prompt tokens the agent can use, if NOT_GIVEN
    or None, agent will run forever"""
    max_completion_tokens: int | None | NotGiven = NOT_GIVEN
    """The maximum number of completion tokens the agent can use, if NOT_GIVEN
    or None, agent will run forever"""


class AgentRunContext(BaseModel):
    """
    Context for the agent run.
    """

    usage: Usage = Field(default_factory=Usage)
    """The usage of the agent."""


class AgentResultStreaming(AsyncIterator[str | ToolCall | ToolCallResult | BasePrompt | Usage | SimpleNamespace]):
    """
    An async iterator that will collect all yielded items by LLM.generate_streaming(). This object is returned
    by `run_streaming`. It can be used in an `async for` loop to process items as they arrive. After the loop completes,
    all items are available under the same names as in AgentResult class.
    """

    def __init__(
        self, generator: AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage]
    ):
        self._generator = generator
        self.content: str = ""
        self.tool_calls: list[ToolCallResult] | None = None
        self.metadata: dict = {}
        self.history: ChatFormat
        self.usage: Usage = Usage()

    def __aiter__(self) -> AsyncIterator[str | ToolCall | ToolCallResult | BasePrompt | Usage | SimpleNamespace]:
        return self

    async def __anext__(self) -> str | ToolCall | ToolCallResult | BasePrompt | Usage | SimpleNamespace:
        try:
            item = await self._generator.__anext__()

            match item:
                case str():
                    self.content += item
                    return item
                case ToolCall():
                    return item
                case ToolCallResult():
                    if self.tool_calls is None:
                        self.tool_calls = []
                    self.tool_calls.append(item)
                    return item
                case BasePrompt():
                    self.history = item.chat
                    return item
                case Usage():
                    self.usage = item
                    return await self.__anext__()
                case SimpleNamespace():
                    result_dict = getattr(item, "result", {})
                    self.content = result_dict.get("content", self.content)
                    self.metadata = result_dict.get("metadata", self.metadata)
                    self.tool_calls = result_dict.get("tool_calls", self.tool_calls)
                    return item
                case _:
                    raise ValueError(f"Unexpected item: {item}")

        except StopAsyncIteration:
            raise


class Agent(
    ConfigurableComponent[AgentOptions[LLMClientOptionsT]], Generic[LLMClientOptionsT, PromptInputT, PromptOutputT]
):
    """
    Agent class that orchestrates the LLM and the prompt, and can call tools.

    Current implementation is highly experimental, and the API is subject to change.
    """

    options_cls: type[AgentOptions] = AgentOptions
    default_module: ClassVar[ModuleType | None] = agents
    configuration_key: ClassVar[str] = "agent"

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        prompt: str | type[Prompt[PromptInputT, PromptOutputT]] | Prompt[PromptInputT, PromptOutputT] | None = None,
        *,
        history: ChatFormat | None = None,
        keep_history: bool = False,
        tools: list[Callable] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        default_options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> None:
        """
        Initialize the agent instance.

        Args:
            llm: The LLM to run the agent.
            prompt: The prompt for the agent. Can be:
                - str: A string prompt that will be used as system message when combined with string input,
                    or as the user message when no input is provided during run().
                - type[Prompt]: A structured prompt class that will be instantiated with the input.
                - Prompt: Already instantiated prompt instance
                - None: No predefined prompt. The input provided to run() will be used as the complete prompt.
            history: The history of the agent.
            keep_history: Whether to keep the history of the agent.
            tools: The tools available to the agent.
            mcp_servers: The MCP servers available to the agent.
            default_options: The default options for the agent run.
        """
        super().__init__(default_options)
        self.llm = llm
        self.prompt = prompt
        self.tools = [Tool.from_callable(tool) for tool in tools or []]
        self.mcp_servers = mcp_servers or []
        self.history = history or []
        self.keep_history = keep_history

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    async def run(
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
    ) -> AgentResult[PromptOutputT]:
        """
        Run the agent. The method is experimental, inputs and outputs may change in the future.

        Args:
            input: The input for the agent run. Can be:
                - str: A string input that will be used as user message.
                - PromptInputT: Structured input for use with structured prompt classes.
                - None: No input. Only valid when a string prompt was provided during initialization.
            options: The options for the agent run.
            context: The context for the agent run.
            post_processors: List of post-processors to apply to the response in order.

        Returns:
            The result of the agent run.

        Raises:
            AgentToolDuplicateError: If the tool names are duplicated.
            AgentToolNotSupportedError: If the selected tool type is not supported.
            AgentToolNotAvailableError: If the selected tool is not available.
            AgentInvalidPromptInputError: If the prompt/input combination is invalid.
            AgentMaxTurnsExceededError: If the maximum number of turns is exceeded.
        """
        result = await self._run_without_post_processing(input, options, context)

        if post_processors:
            for processor in post_processors:
                result = await processor.process(result, self)

        return result

    async def _run_without_post_processing(
        self,
        input: str | PromptInputT | None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
    ) -> AgentResult[PromptOutputT]:
        """
        Run the agent without applying post-processors.
        """
        if context is None:
            context = AgentRunContext()

        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or self.llm.default_options

        prompt_with_history = self._get_prompt_with_history(input)
        tools_mapping = await self._get_all_tools()
        tool_calls = []

        turn_count = 0
        max_turns = merged_options.max_turns
        max_turns = 10 if max_turns is NOT_GIVEN else max_turns
        with trace(input=input, options=merged_options) as outputs:
            while not max_turns or turn_count < max_turns:
                self._check_token_limits(merged_options, context.usage, prompt_with_history, self.llm)
                response = cast(
                    LLMResponseWithMetadata[PromptOutputT],
                    await self.llm.generate_with_metadata(
                        prompt=prompt_with_history,
                        tools=[tool.to_function_schema() for tool in tools_mapping.values()],
                        options=self._get_llm_options(llm_options, merged_options, context.usage),
                    ),
                )
                context.usage += response.usage or Usage()

                if not response.tool_calls:
                    break

                for tool_call in response.tool_calls:
                    result = await self._execute_tool(tool_call=tool_call, tools_mapping=tools_mapping, context=context)
                    tool_calls.append(result)

                    prompt_with_history = prompt_with_history.add_tool_use_message(**result.__dict__)

                turn_count += 1
            else:
                raise AgentMaxTurnsExceededError(cast(int, max_turns))

            outputs.result = {
                "content": response.content,
                "metadata": response.metadata,
                "tool_calls": tool_calls or None,
            }

            prompt_with_history = prompt_with_history.add_assistant_message(response.content)

            if self.keep_history:
                self.history = prompt_with_history.chat

            return AgentResult(
                content=response.content,
                metadata=response.metadata,
                tool_calls=tool_calls or None,
                history=prompt_with_history.chat,
                usage=context.usage,
            )

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
        *,
        allow_non_streaming: bool = False,
    ) -> AgentResultStreaming: ...

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
        *,
        allow_non_streaming: bool = False,
    ) -> AgentResultStreaming: ...

    def run_streaming(
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
        *,
        allow_non_streaming: bool = False,
    ) -> AgentResultStreaming:
        """
        This method returns an `AgentResultStreaming` object that can be asynchronously
        iterated over. After the loop completes, all items are available under the same names as in AgentResult class.

        Args:
            input: The input for the agent run.
            options: The options for the agent run.
            context: The context for the agent run.
            post_processors: List of post-processors to apply to the response in order.
            allow_non_streaming: Whether to allow non-streaming post-processors.

        Returns:
            A `StreamingResult` object for iteration and collection.

        Raises:
            AgentToolDuplicateError: If the tool names are duplicated.
            AgentToolNotSupportedError: If the selected tool type is not supported.
            AgentToolNotAvailableError: If the selected tool is not available.
            AgentInvalidPromptInputError: If the prompt/input combination is invalid.
            AgentMaxTurnsExceededError: If the maximum number of turns is exceeded.
            AgentInvalidPostProcessorError: If the post-processor is invalid.
        """
        if post_processors:
            if not allow_non_streaming and any(not p.supports_streaming for p in post_processors):
                raise AgentInvalidPostProcessorError(
                    reason="Non-streaming post-processors are not allowed when allow_non_streaming is False"
                )
            generator = self._stream_with_post_processing(input, options, context, post_processors)
        else:
            generator = self._stream_internal(input, options, context)

        return AgentResultStreaming(generator)

    async def _stream_internal(
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
    ) -> AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage]:
        if context is None:
            context = AgentRunContext()

        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or self.llm.default_options

        prompt_with_history = self._get_prompt_with_history(input)
        tools_mapping = await self._get_all_tools()
        turn_count = 0
        max_turns = merged_options.max_turns
        max_turns = 10 if max_turns is NOT_GIVEN else max_turns
        with trace(input=input, options=merged_options) as outputs:
            while not max_turns or turn_count < max_turns:
                returned_tool_call = False
                self._check_token_limits(merged_options, context.usage, prompt_with_history, self.llm)
                streaming_result = self.llm.generate_streaming(
                    prompt=prompt_with_history,
                    tools=[tool.to_function_schema() for tool in tools_mapping.values()],
                    options=self._get_llm_options(llm_options, merged_options, context.usage),
                )
                async for chunk in streaming_result:
                    yield chunk

                    if isinstance(chunk, ToolCall):
                        result = await self._execute_tool(tool_call=chunk, tools_mapping=tools_mapping, context=context)
                        yield result
                        prompt_with_history = prompt_with_history.add_tool_use_message(**result.__dict__)
                        returned_tool_call = True
                turn_count += 1
                if streaming_result.usage:
                    context.usage += streaming_result.usage

                if not returned_tool_call:
                    break
            else:
                raise AgentMaxTurnsExceededError(cast(int, max_turns))

            yield context.usage
            yield prompt_with_history
            if self.keep_history:
                self.history = prompt_with_history.chat
            yield outputs

    @staticmethod
    def _check_token_limits(
        options: AgentOptions[LLMClientOptionsT], usage: Usage, prompt: BasePrompt, llm: LLM[LLMClientOptionsT]
    ) -> None:
        if options.max_prompt_tokens or options.max_total_tokens:
            next_prompt_tokens = llm.count_tokens(prompt)
            if options.max_prompt_tokens and next_prompt_tokens > options.max_prompt_tokens - usage.prompt_tokens:
                raise AgentMaxTokensExceededError("prompt", options.max_prompt_tokens, next_prompt_tokens)
            if options.max_total_tokens and next_prompt_tokens > options.max_total_tokens - usage.total_tokens:
                raise AgentNextPromptOverLimitError(
                    "total", options.max_total_tokens, usage.total_tokens, next_prompt_tokens
                )

        if options.max_total_tokens and usage.total_tokens > options.max_total_tokens:
            raise AgentMaxTokensExceededError("total", options.max_total_tokens, usage.total_tokens)
        if options.max_prompt_tokens and usage.prompt_tokens > options.max_prompt_tokens:
            raise AgentMaxTokensExceededError("prompt", options.max_prompt_tokens, usage.prompt_tokens)
        if options.max_completion_tokens and usage.completion_tokens > options.max_completion_tokens:
            raise AgentMaxTokensExceededError("completion", options.max_completion_tokens, usage.completion_tokens)

    @staticmethod
    def _get_llm_options(
        llm_options: LLMClientOptionsT, options: AgentOptions[LLMClientOptionsT], usage: Usage
    ) -> LLMClientOptionsT:
        actual_limits: list[int] = [
            limit
            for limit in (options.max_total_tokens, options.max_prompt_tokens, options.max_completion_tokens)
            if isinstance(limit, int)
        ]

        if not actual_limits:
            return llm_options

        llm_options.max_tokens = min(actual_limits) - usage.total_tokens
        return llm_options

    def _get_prompt_with_history(self, input: PromptInputT) -> SimplePrompt | Prompt[PromptInputT, PromptOutputT]:
        curr_history = deepcopy(self.history)
        if isinstance(self.prompt, type) and issubclass(self.prompt, Prompt):
            if self.keep_history:
                self.prompt = self.prompt(input, curr_history)
                return self.prompt
            else:
                return self.prompt(input, curr_history)

        if isinstance(self.prompt, Prompt):
            self.prompt.add_user_message(input)
            return self.prompt

        if isinstance(self.prompt, str) and isinstance(input, str):
            system_prompt = {"role": "system", "content": self.prompt}
            if len(curr_history) == 0:
                curr_history.append(system_prompt)
            else:
                system_idx = next((i for i, msg in enumerate(curr_history) if msg["role"] == "system"), -1)
                if system_idx == -1:
                    curr_history.insert(0, system_prompt)
                else:
                    curr_history[system_idx] = system_prompt
            incoming_user_prompt = input
        elif isinstance(self.prompt, str) and input is None:
            incoming_user_prompt = self.prompt
        elif isinstance(input, str):
            incoming_user_prompt = input
        else:
            raise AgentInvalidPromptInputError(self.prompt, input)

        curr_history.append({"role": "user", "content": incoming_user_prompt})

        return SimplePrompt(curr_history)

    async def _get_all_tools(self) -> dict[str, Tool]:
        tools_mapping = {}
        all_tools = list(self.tools)

        server_tools = await asyncio.gather(*[get_tools(server) for server in self.mcp_servers])
        for tools in server_tools:
            all_tools.extend(tools)

        for tool in all_tools:
            if tool.name in tools_mapping:
                raise AgentToolDuplicateError(tool.name)
            tools_mapping[tool.name] = tool

        return tools_mapping

    @staticmethod
    async def _execute_tool(
        tool_call: ToolCall, tools_mapping: dict[str, Tool], context: AgentRunContext | None = None
    ) -> ToolCallResult:
        if tool_call.type != "function":
            raise AgentToolNotSupportedError(tool_call.type)

        if tool_call.name not in tools_mapping:
            raise AgentToolNotAvailableError(tool_call.name)

        tool = tools_mapping[tool_call.name]

        try:
            call_args = tool_call.arguments.copy()
            if tool.context_var_name:
                call_args[tool.context_var_name] = context

            tool_output = (
                await tool.on_tool_call(**call_args)
                if iscoroutinefunction(tool.on_tool_call)
                else tool.on_tool_call(**call_args)
            )
        except Exception as e:
            raise AgentToolExecutionError(tool_call.name, e) from e

        return ToolCallResult(
            id=tool_call.id,
            name=tool_call.name,
            arguments=tool_call.arguments,
            result=tool_output,
        )

    @requires_dependencies(["a2a.types"], "a2a")
    async def get_agent_card(
        self,
        name: str,
        description: str,
        version: str = "0.0.0",
        host: str = "127.0.0.1",
        port: int = 8000,
        protocol: str = "http",
        default_input_modes: list[str] | None = None,
        default_output_modes: list[str] | None = None,
        capabilities: "AgentCapabilities | None" = None,
        skills: list["AgentSkill"] | None = None,
    ) -> "AgentCard":
        """
        Create an AgentCard that encapsulates metadata about the agent,
        such as its name, version, description, network location, supported input/output modes,
        capabilities, and skills.

        Args:
            name: Human-readable name of the agent.
            description: A brief description of the agent.
            version: Version string of the agent. Defaults to "0.0.0".
            host: Hostname or IP where the agent will be served. Defaults to "0.0.0.0".
            port: Port number on which the agent listens. Defaults to 8000.
            protocol: URL scheme (e.g. "http" or "https"). Defaults to "http".
            default_input_modes: List of input content modes supported by the agent. Defaults to ["text"].
            default_output_modes: List of output content modes supported. Defaults to ["text"].
            capabilities: Agent capabilities; if None, defaults to empty capabilities.
            skills: List of AgentSkill objects representing the agent's skills.
                If None, attempts to extract skills from the agent's registered tools.

        Returns:
            An A2A-compliant agent descriptor including URL and capabilities.
        """
        return AgentCard(
            name=name,
            version=version,
            description=description,
            url=f"{protocol}://{host}:{port}",
            defaultInputModes=default_input_modes or ["text"],
            defaultOutputModes=default_output_modes or ["text"],
            skills=skills or await self._extract_agent_skills(),
            capabilities=capabilities or AgentCapabilities(),
        )

    async def _extract_agent_skills(self) -> list["AgentSkill"]:
        """
        The skill representation with name, id, description, and tags.
        """
        all_tools = await self._get_all_tools()
        return [
            AgentSkill(
                name=tool.name.replace("_", " ").title(),
                id=tool.name,
                description=f"{tool.description}\n\nParameters:\n{tool.parameters}",
                tags=[],
            )
            for tool in all_tools.values()
        ]

    async def _stream_with_post_processing(
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        post_processors: list[BasePostProcessor] | None = None,
    ) -> AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage]:
        """
        Stream with support for both streaming and non-streaming post-processors.

        Streaming processors get chunks in real-time via process_streaming().
        Non-streaming processors get the complete result via process().
        """
        input = cast(PromptInputT, input)

        streaming_processors = [p for p in post_processors or [] if p.supports_streaming]
        non_streaming_processors = [p for p in post_processors or [] if not p.supports_streaming]

        accumulated_content = ""
        tool_call_results: list[ToolCallResult] = []
        usage: Usage = Usage()
        prompt_with_history: BasePrompt | None = None

        async for chunk in self._stream_internal(input, options, context):
            processed_chunk = chunk
            for processor in streaming_processors:
                processed_chunk = await processor.process_streaming(chunk=processed_chunk, agent=self)
                if processed_chunk is None:
                    break

            if isinstance(processed_chunk, str):
                accumulated_content += processed_chunk
            elif isinstance(processed_chunk, ToolCallResult):
                tool_call_results.append(processed_chunk)
            elif isinstance(processed_chunk, Usage):
                usage = processed_chunk
            elif isinstance(processed_chunk, BasePrompt):
                prompt_with_history = processed_chunk

            if processed_chunk is not None:
                yield processed_chunk

        if non_streaming_processors and prompt_with_history:
            agent_result = AgentResult(
                content=accumulated_content,
                metadata={},
                tool_calls=tool_call_results or None,
                history=prompt_with_history.chat,
                usage=usage,
            )

            current_result = agent_result
            for processor in non_streaming_processors:
                current_result = await processor.process(current_result, self)

            yield current_result.usage
            yield prompt_with_history
            yield SimpleNamespace(
                result={
                    "content": current_result.content,
                    "metadata": current_result.metadata,
                    "tool_calls": current_result.tool_calls,
                }
            )
