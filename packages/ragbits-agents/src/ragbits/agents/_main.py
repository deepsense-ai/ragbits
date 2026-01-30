import asyncio
import types
import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from collections.abc import AsyncGenerator as _AG
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from inspect import iscoroutinefunction
from types import ModuleType, SimpleNamespace
from typing import Any, ClassVar, Generic, Literal, TypeVar, Union, cast, overload

from pydantic import (
    BaseModel,
    Field,
)
from typing_extensions import Self

from ragbits import agents
from ragbits.agents.confirmation import ConfirmationRequest
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
from ragbits.agents.hooks import (
    Hook,
    HookManager,
)
from ragbits.agents.mcp.server import MCPServer, MCPServerStdio, MCPServerStreamableHttp
from ragbits.agents.mcp.utils import get_tools
from ragbits.agents.post_processors.base import (
    BasePostProcessor,
    PostProcessor,
    StreamingPostProcessor,
    stream_with_post_processing,
)
from ragbits.agents.tool import Tool, ToolCallResult, ToolChoice, ToolReturn
from ragbits.core.audit.traces import trace
from ragbits.core.llms.base import (
    LLM,
    LLMClientOptionsT,
    LLMOptions,
    LLMResponseWithMetadata,
    Reasoning,
    ToolCall,
    Usage,
)
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePrompt, ChatFormat, SimplePrompt
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill
    from pydantic_ai import Agent as PydanticAIAgent
    from pydantic_ai import mcp

    from ragbits.core.llms import LiteLLM

_Input = TypeVar("_Input", bound=BaseModel)
_Output = TypeVar("_Output")


@dataclass
class DownstreamAgentResult:
    """
    Represents a streamed item from a downstream agent while executing a tool.
    """

    agent_id: str | None
    """ID of the downstream agent."""
    item: Union[
        str,
        ToolCall,
        ToolCallResult,
        "DownstreamAgentResult",
        BasePrompt,
        Usage,
        SimpleNamespace,
        ConfirmationRequest,
    ]
    """The streamed item from the downstream agent."""


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
    reasoning_traces: list[str] | None = None
    """Reasoning traces from the agent run (only if log_reasoning is enabled)."""


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
    log_reasoning: bool = False
    """Whether to log/persist reasoning traces for debugging and evaluation."""
    parallel_tool_calling: bool = False
    """Whether to run the tools concurrently if multiple of them are requested by an LLM. Synchronous tools will be
    run in a separate thread using `asyncio.to_thread`"""


DepsT = TypeVar("DepsT")


class AgentDependencies(BaseModel, Generic[DepsT]):
    """
    Container for agent runtime dependencies.

    Becomes immutable after first attribute access.
    """

    model_config = {"arbitrary_types_allowed": True}

    _frozen: bool
    _value: DepsT | None

    def __init__(self, value: DepsT | None = None) -> None:
        super().__init__()
        self._value = value
        self._frozen = False

    def __setattr__(self, name: str, value: object) -> None:
        is_frozen = False
        if name != "_frozen":
            try:
                is_frozen = object.__getattribute__(self, "_frozen")
            except AttributeError:
                is_frozen = False

        if is_frozen and name not in {"_frozen"}:
            raise RuntimeError("Dependencies are immutable after first access")

        super().__setattr__(name, value)

    @property
    def value(self) -> DepsT | None:
        return self._value

    @value.setter
    def value(self, value: DepsT) -> None:
        if self._frozen:
            raise RuntimeError("Dependencies are immutable after first access")
        self._value = value

    def _freeze(self) -> None:
        if not self._frozen:
            self._frozen = True

    def __getattr__(self, name: str) -> object:
        value = object.__getattribute__(self, "_value")
        if value is None:
            raise AttributeError(name)
        self._freeze()
        return getattr(value, name)

    def __contains__(self, key: str) -> bool:
        value = object.__getattribute__(self, "_value")
        return hasattr(value, key) if value is not None else False


class AgentRunContext(BaseModel, Generic[DepsT]):
    """Context for the agent run."""

    model_config = {"arbitrary_types_allowed": True}

    deps: AgentDependencies[DepsT] = Field(default_factory=lambda: AgentDependencies())
    """Container for external dependencies."""
    usage: Usage = Field(default_factory=Usage)
    """The usage of the agent."""
    stream_downstream_events: bool = False
    """Whether to stream events from downstream agents when tools execute other agents."""
    downstream_agents: dict[str, "Agent"] = Field(default_factory=dict)
    """Registry of all agents that participated in this run"""
    tool_confirmations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of confirmed/declined tool executions. Each entry has 'confirmation_id' and 'confirmed' "
        "(bool)",
    )

    def register_agent(self, agent: "Agent") -> None:
        """
        Register a downstream agent in this context.

        Args:
            agent: The agent instance to register.
        """
        self.downstream_agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> "Agent | None":
        """
        Retrieve a registered downstream agent by its ID.

        Args:
            agent_id: The unique identifier of the agent.

        Returns:
            The Agent instance if found, otherwise None.
        """
        return self.downstream_agents.get(agent_id)


class AgentResultStreaming(
    AsyncIterator[
        str
        | ToolCall
        | ToolCallResult
        | BasePrompt
        | Usage
        | SimpleNamespace
        | DownstreamAgentResult
        | ConfirmationRequest
    ]
):
    """
    An async iterator that will collect all yielded items by LLM.generate_streaming(). This object is returned
    by `run_streaming`. It can be used in an `async for` loop to process items as they arrive. After the loop completes,
    all items are available under the same names as in AgentResult class.
    """

    def __init__(
        self,
        generator: AsyncGenerator[
            str
            | ToolCall
            | ToolCallResult
            | DownstreamAgentResult
            | SimpleNamespace
            | BasePrompt
            | Usage
            | ConfirmationRequest,
            None,
        ],
    ):
        self._generator = generator
        self.content: str = ""
        self.tool_calls: list[ToolCallResult] | None = None
        self.downstream: dict[str | None, list[str | ToolCall | ToolCallResult]] = {}
        self.metadata: dict = {}
        self.history: ChatFormat
        self.usage: Usage = Usage()

    def __aiter__(
        self,
    ) -> AsyncIterator[
        str
        | ToolCall
        | ToolCallResult
        | BasePrompt
        | Usage
        | SimpleNamespace
        | DownstreamAgentResult
        | ConfirmationRequest
    ]:
        return self

    async def __anext__(  # noqa: PLR0912
        self,
    ) -> (
        str
        | ToolCall
        | ToolCallResult
        | BasePrompt
        | Usage
        | SimpleNamespace
        | DownstreamAgentResult
        | ConfirmationRequest
    ):
        try:
            item = await self._generator.__anext__()

            match item:
                case str():
                    self.content += item
                case ToolCall():
                    pass
                case ToolCallResult():
                    if self.tool_calls is None:
                        self.tool_calls = []
                    self.tool_calls.append(item)
                case ConfirmationRequest():
                    # Pass through confirmation requests to the frontend
                    pass
                case DownstreamAgentResult():
                    if item.agent_id not in self.downstream:
                        self.downstream[item.agent_id] = []
                    if isinstance(item.item, str | ToolCall | ToolCallResult):
                        self.downstream[item.agent_id].append(item.item)
                case BasePrompt():
                    item.add_assistant_message(self.content)
                    self.history = item.chat
                case Usage():
                    self.usage = item
                    # continue loop instead of tail recursion
                    return await self.__anext__()
                case SimpleNamespace():
                    result_dict = getattr(item, "result", {})
                    self.content = result_dict.get("content", self.content)
                    self.metadata = result_dict.get("metadata", self.metadata)
                    self.tool_calls = result_dict.get("tool_calls", self.tool_calls)
                case _:
                    raise ValueError(f"Unexpected item: {item}")

            return item

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
    # Syntax sugar fields
    user_prompt: ClassVar[str] = "{{ input }}"
    system_prompt: ClassVar[str | None] = None
    input_type: PromptInputT | None = None
    prompt_cls: ClassVar[type[Prompt] | None] = None

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        name: str | None = None,
        description: str | None = None,
        prompt: str | type[Prompt[PromptInputT, PromptOutputT]] | Prompt[PromptInputT, PromptOutputT] | None = None,
        *,
        history: ChatFormat | None = None,
        keep_history: bool = False,
        tools: list[Callable] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        hooks: list[Hook] | None = None,
        default_options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> None:
        """
        Initialize the agent instance.

        Args:
            llm: The LLM to run the agent.
            name: Optional name of the agent. Used to identify the agent instance.
            description: Optional description of the agent.
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
            hooks: List of tool hooks to register for tool lifecycle events.
            default_options: The default options for the agent run.
        """
        super().__init__(default_options)
        self.id = uuid.uuid4().hex[:8]
        self.llm = llm
        self.prompt = prompt
        self.name = name
        self.description = description
        self.tools = []
        for tool in tools or []:
            if isinstance(tool, tuple):
                agent, kwargs = tool
                self.tools.append(Tool.from_agent(agent, **kwargs))
            elif isinstance(tool, Agent):
                self.tools.append(Tool.from_agent(tool))
            elif isinstance(tool, Tool):
                self.tools.append(tool)
            else:
                self.tools.append(Tool.from_callable(tool))
        self.mcp_servers = mcp_servers or []
        self.history = history or []
        self.keep_history = keep_history
        self.hook_manager = HookManager(hooks)

        if getattr(self, "system_prompt", None) and not getattr(self, "input_type", None):
            raise ValueError(
                f"Agent {type(self).__name__} defines a system_prompt but has no input_type. ",
                "Use Agent.prompt decorator to properly assign it.",
            )

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    async def run(
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
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
            tool_choice: Parameter that allows to control what tool is used at first call. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - Callable: one of provided tools
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
        result = await self._run_without_post_processing(input, options, context, tool_choice)

        if post_processors:
            for processor in post_processors:
                result = await processor.process(result, self, options, context)

        return result

    async def _run_without_post_processing(
        self,
        input: str | PromptInputT | None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
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
        reasoning_traces: list[str] = []

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
                        tool_choice=tool_choice if tool_choice and turn_count == 0 else None,
                        options=self._get_llm_options(llm_options, merged_options, context.usage),
                    ),
                )
                context.usage += response.usage or Usage()

                if merged_options.log_reasoning and response.reasoning:
                    reasoning_traces.append(response.reasoning)

                if not response.tool_calls:
                    break

                async for result in self._execute_tool_calls(
                    response.tool_calls, tools_mapping, context, merged_options.parallel_tool_calling
                ):
                    if isinstance(result, ToolCallResult):
                        tool_calls.append(result)
                        prompt_with_history = prompt_with_history.add_tool_use_message(
                            id=result.id, name=result.name, arguments=result.arguments, result=result.result
                        )

                turn_count += 1
            else:
                raise AgentMaxTurnsExceededError(cast(int, max_turns))

            outputs.result = {
                "content": response.content,
                "metadata": response.metadata,
                "tool_calls": tool_calls or None,
            }
            if merged_options.log_reasoning and reasoning_traces:
                outputs.result["reasoning_traces"] = reasoning_traces

            prompt_with_history = prompt_with_history.add_assistant_message(response.content)

            if self.keep_history:
                self.history = prompt_with_history.chat

            return AgentResult(
                content=response.content,
                metadata=response.metadata,
                tool_calls=tool_calls or None,
                history=prompt_with_history.chat,
                usage=context.usage,
                reasoning_traces=reasoning_traces or None,
            )

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[StreamingPostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
        *,
        allow_non_streaming: bool = False,
    ) -> AgentResultStreaming: ...

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[BasePostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
        *,
        allow_non_streaming: Literal[True],
    ) -> AgentResultStreaming: ...

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[StreamingPostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
        *,
        allow_non_streaming: bool = False,
    ) -> AgentResultStreaming: ...

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: list[BasePostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]] | None = None,
        *,
        allow_non_streaming: Literal[True],
    ) -> AgentResultStreaming: ...

    def run_streaming(
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
        post_processors: (
            list[StreamingPostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]]
            | list[BasePostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]]
            | None
        ) = None,
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
            tool_choice: Parameter that allows to control what tool is used at first call. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - Callable: one of provided tools
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
        generator = self._stream_internal(
            input=input,
            options=options,
            context=context,
            tool_choice=tool_choice,
        )

        if post_processors:
            if not allow_non_streaming and any(not p.supports_streaming for p in post_processors):
                raise AgentInvalidPostProcessorError(
                    reason="Non-streaming post-processors are not allowed when allow_non_streaming is False"
                )

            generator = cast(
                _AG[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest],
                generator,
            )
            generator = stream_with_post_processing(generator, post_processors, self)

        return AgentResultStreaming(generator)

    async def _stream_internal(  # noqa: PLR0912, PLR0915
        self,
        input: str | PromptInputT | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
        context: AgentRunContext | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[
        str
        | ToolCall
        | ToolCallResult
        | DownstreamAgentResult
        | SimpleNamespace
        | BasePrompt
        | Usage
        | ConfirmationRequest,
        None,
    ]:
        if context is None:
            context = AgentRunContext()

        context.register_agent(cast(Agent[Any, Any, str], self))

        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or self.llm.default_options

        prompt_with_history = self._get_prompt_with_history(input)
        tools_mapping = await self._get_all_tools()
        turn_count = 0
        max_turns = merged_options.max_turns
        max_turns = 10 if max_turns is NOT_GIVEN else max_turns
        reasoning_traces: list[str] = []

        with trace(input=input, options=merged_options) as outputs:
            # Track confirmation IDs that have been requested to detect loops
            requested_confirmation_ids: set[str] = set()
            # Track if we should generate text-only summary (no tools)
            generate_text_only = False

            while not max_turns or turn_count < max_turns:
                returned_tool_call = False
                self._check_token_limits(merged_options, context.usage, prompt_with_history, self.llm)

                # Determine tool choice for this turn
                current_tool_choice: ToolChoice | None
                current_tools: list[Callable[..., Any] | dict[Any, Any]]

                if generate_text_only:
                    # Force text-only generation (no tool calls)
                    # Don't set tool_choice when tools is empty (causes OpenAI error)
                    current_tool_choice = None
                    current_tools = []
                elif tool_choice and turn_count == 0:
                    current_tool_choice = tool_choice
                    current_tools = [tool.to_function_schema() for tool in tools_mapping.values()]
                else:
                    current_tool_choice = None
                    current_tools = [tool.to_function_schema() for tool in tools_mapping.values()]

                streaming_result = self.llm.generate_streaming(
                    prompt=prompt_with_history,
                    tools=current_tools,
                    tool_choice=current_tool_choice,
                    options=self._get_llm_options(llm_options, merged_options, context.usage),
                )
                tool_chunks = []
                async for chunk in streaming_result:
                    if isinstance(chunk, Reasoning) and merged_options.log_reasoning:
                        reasoning_traces.append(str(chunk))
                    yield chunk
                    if isinstance(chunk, ToolCall):
                        tool_chunks.append(chunk)

                if len(tool_chunks) > 0:
                    has_pending_confirmation = False
                    current_turn_confirmation_ids: set[str] = set()

                    async for result in self._execute_tool_calls(
                        tool_chunks, tools_mapping, context, merged_options.parallel_tool_calling
                    ):
                        yield result
                        if isinstance(result, ConfirmationRequest):
                            # Mark that we have a pending confirmation
                            has_pending_confirmation = True
                            current_turn_confirmation_ids.add(result.confirmation_id)
                        elif isinstance(result, ToolCallResult):
                            # Add ALL tool results to history (including pending confirmations)
                            # This allows the agent to see them in the next turn
                            prompt_with_history = prompt_with_history.add_tool_use_message(
                                id=result.id, name=result.name, arguments=result.arguments, result=result.result
                            )
                            returned_tool_call = True

                    # If we have pending confirmations, prepare for text-only summary generation
                    if has_pending_confirmation:
                        # Check if we've already requested these confirmations (infinite loop detection)
                        if current_turn_confirmation_ids & requested_confirmation_ids:
                            break
                        # Add to tracking set
                        requested_confirmation_ids.update(current_turn_confirmation_ids)
                        # Set flag to generate text-only summary in next turn
                        generate_text_only = True

                # If we just generated text-only summary, we're done
                if generate_text_only and len(tool_chunks) == 0:
                    break

                turn_count += 1
                if streaming_result.usage:
                    context.usage += streaming_result.usage

                # Break if no tool was called
                if not returned_tool_call:
                    break
            else:
                raise AgentMaxTurnsExceededError(cast(int, max_turns))

            yield context.usage
            yield prompt_with_history
            if self.keep_history:
                self.history = prompt_with_history.chat

            if merged_options.log_reasoning and reasoning_traces:
                outputs.result = {"reasoning_traces": reasoning_traces}

            yield outputs

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall],
        tools_mapping: dict[str, Tool],
        context: AgentRunContext,
        parallel_tool_calling: bool,
    ) -> AsyncGenerator[ToolCallResult | DownstreamAgentResult | ConfirmationRequest, None]:
        """Execute tool calls either in parallel or sequentially based on `parallel_tool_calling` value."""
        if parallel_tool_calling:
            queue: asyncio.Queue = asyncio.Queue()

            async def consume_tool(tool: ToolCall) -> None:
                async for tool_result in self._execute_tool(
                    tool_call=tool, tools_mapping=tools_mapping, context=context
                ):
                    await queue.put(tool_result)

            async def monitor() -> None:
                tasks = [asyncio.create_task(consume_tool(tool)) for tool in tool_calls]
                await asyncio.gather(*tasks)
                await queue.put(None)

            asyncio.create_task(monitor())
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item

        else:
            for tool_call in tool_calls:
                async for result in self._execute_tool(
                    tool_call=tool_call, tools_mapping=tools_mapping, context=context
                ):
                    yield result

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

    def _prepare_synthesized_prompt(
        self, input: PromptInputT
    ) -> SimplePrompt | Prompt[PromptInputT, PromptOutputT] | None:
        curr_history = deepcopy(self.history)
        if (
            hasattr(self, "prompt_cls")
            and self.prompt_cls
            and isinstance(self.prompt_cls, type)
            and issubclass(self.prompt_cls, Prompt)
        ):
            prompt_cls = cast(type[Prompt[PromptInputT, PromptOutputT]], self.prompt_cls)
            if self.keep_history:
                self.prompt = cast(Prompt[PromptInputT, PromptOutputT], prompt_cls(input, curr_history))
                return self.prompt
            else:
                return cast(Prompt[PromptInputT, PromptOutputT], prompt_cls(input))

        if isinstance(self.prompt, type) and issubclass(self.prompt, Prompt):
            if self.keep_history:
                self.prompt = self.prompt(input, curr_history)
                return self.prompt
            else:
                return self.prompt(input)

        return None

    def _get_prompt_with_history(self, input: PromptInputT) -> SimplePrompt | Prompt[PromptInputT, PromptOutputT]:
        curr_history = deepcopy(self.history)
        new_prompt = self._prepare_synthesized_prompt(input)

        if new_prompt:
            return new_prompt

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

    async def _execute_tool(
        self,
        tool_call: ToolCall,
        tools_mapping: dict[str, Tool],
        context: AgentRunContext,
    ) -> AsyncGenerator[ToolCallResult | DownstreamAgentResult | ConfirmationRequest, None]:
        if tool_call.type != "function":
            raise AgentToolNotSupportedError(tool_call.type)
        if tool_call.name not in tools_mapping:
            raise AgentToolNotAvailableError(tool_call.name)

        tool = tools_mapping[tool_call.name]

        # Execute PRE_TOOL hooks with chaining
        pre_tool_result = await self.hook_manager.execute_pre_tool(
            tool_call=tool_call,
            context=context,
        )

        # Check decision
        if pre_tool_result.decision == "deny":
            yield ToolCallResult(
                id=tool_call.id,
                name=tool_call.name,
                arguments=tool_call.arguments,
                result=pre_tool_result.reason or "Tool execution denied",
            )
            return
        # Handle "ask" decision from hooks
        elif pre_tool_result.decision == "ask" and pre_tool_result.confirmation_request is not None:
            yield pre_tool_result.confirmation_request

            yield ToolCallResult(
                id=tool_call.id,
                name=tool_call.name,
                arguments=tool_call.arguments,
                result=pre_tool_result.reason or "Hook requires user confirmation",
            )
            return

        # Always update arguments (chained from hooks)
        tool_call.arguments = pre_tool_result.arguments

        tool_error: Exception | None = None

        with trace(agent_id=self.id, tool_name=tool_call.name, tool_arguments=tool_call.arguments) as outputs:
            try:
                call_args = tool_call.arguments.copy()
                if tool.context_var_name:
                    call_args[tool.context_var_name] = context

                tool_output = await (
                    tool.on_tool_call(**call_args)
                    if iscoroutinefunction(tool.on_tool_call)
                    else asyncio.to_thread(tool.on_tool_call, **call_args)
                )

                if isinstance(tool_output, ToolReturn):
                    tool_return = tool_output
                elif isinstance(tool_output, AgentResultStreaming):
                    async for downstream_item in tool_output:
                        if context.stream_downstream_events:
                            yield DownstreamAgentResult(agent_id=tool.id, item=downstream_item)
                    metadata = {
                        "metadata": tool_output.metadata,
                        "tool_calls": tool_output.tool_calls,
                        "usage": tool_output.usage,
                    }
                    tool_return = ToolReturn(value=tool_output.content, metadata=metadata)
                else:
                    tool_return = ToolReturn(value=tool_output, metadata=None)

                outputs.result = {
                    "tool_output": tool_return.value,
                    "tool_call_id": tool_call.id,
                }

            except Exception as e:
                tool_error = e
                outputs.result = {
                    "error": str(e),
                    "tool_call_id": tool_call.id,
                }

        # Execute POST_TOOL hooks with chaining
        post_tool_result = await self.hook_manager.execute_post_tool(
            tool_call=tool_call,
            output=tool_output,
            error=tool_error,
        )
        tool_output = post_tool_result.output

        # Raise error after hooks have been executed
        if tool_error:
            raise AgentToolExecutionError(tool_call.name, tool_error) from tool_error

        yield ToolCallResult(
            id=tool_call.id,
            name=tool_call.name,
            arguments=tool_call.arguments,
            result=tool_return.value,
            metadata=tool_return.metadata,
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

    @requires_dependencies("pydantic_ai")
    def to_pydantic_ai(self) -> "PydanticAIAgent":
        """
        Convert ragbits agent instance into a `pydantic_ai.Agent` representation.

        Returns:
            PydanticAIAgent: The equivalent Pydantic-based agent configuration.

        Raises:
            ValueError: If the `prompt` is not a string or a `Prompt` instance.
        """
        mcp_servers: list[mcp.MCPServerStdio | mcp.MCPServerHTTP] = []

        if not self.prompt:
            raise ValueError("Prompt is required but was None.")

        if isinstance(self.prompt, str):
            system_prompt = self.prompt
        else:
            if not self.prompt.system_prompt:
                raise ValueError("System prompt is required but was None.")
            system_prompt = self.prompt.system_prompt

        for mcp_server in self.mcp_servers:
            if isinstance(mcp_server, MCPServerStdio):
                mcp_servers.append(
                    mcp.MCPServerStdio(
                        command=mcp_server.params.command, args=mcp_server.params.args, env=mcp_server.params.env
                    )
                )
            elif isinstance(mcp_server, MCPServerStreamableHttp):
                timeout = mcp_server.params["timeout"]
                sse_timeout = mcp_server.params["sse_read_timeout"]

                mcp_servers.append(
                    mcp.MCPServerHTTP(
                        url=mcp_server.params["url"],
                        headers=mcp_server.params["headers"],
                        timeout=timeout.total_seconds() if isinstance(timeout, timedelta) else timeout,
                        sse_read_timeout=sse_timeout.total_seconds()
                        if isinstance(sse_timeout, timedelta)
                        else sse_timeout,
                    )
                )
        return PydanticAIAgent(
            model=self.llm.model_name,
            system_prompt=system_prompt,
            tools=[tool.to_pydantic_ai() for tool in self.tools],
            mcp_servers=mcp_servers,
        )

    @classmethod
    @requires_dependencies("pydantic_ai")
    def from_pydantic_ai(cls, pydantic_ai_agent: "PydanticAIAgent") -> Self:
        """
        Construct an agent instance from a `pydantic_ai.Agent` representation.

        Args:
            pydantic_ai_agent: A Pydantic-based agent configuration.

        Returns:
            An instance of the agent class initialized from the Pydantic representation.
        """
        mcp_servers: list[MCPServerStdio | MCPServerStreamableHttp] = []
        for mcp_server in pydantic_ai_agent._mcp_servers:
            if isinstance(mcp_server, mcp.MCPServerStdio):
                mcp_servers.append(
                    MCPServerStdio(
                        params={
                            "command": mcp_server.command,
                            "args": list(mcp_server.args),
                            "env": mcp_server.env or {},
                        }
                    )
                )
            elif isinstance(mcp_server, mcp.MCPServerHTTP):
                headers = mcp_server.headers or {}

                mcp_servers.append(
                    MCPServerStreamableHttp(
                        params={
                            "url": mcp_server.url,
                            "headers": {str(k): str(v) for k, v in headers.items()},
                            "sse_read_timeout": mcp_server.sse_read_timeout,
                            "timeout": mcp_server.timeout,
                        }
                    )
                )

        if not pydantic_ai_agent.model:
            raise ValueError("Missing LLM in `pydantic_ai.Agent` instance")
        elif isinstance(pydantic_ai_agent.model, str):
            model_name = pydantic_ai_agent.model
        else:
            model_name = pydantic_ai_agent.model.model_name

        return cls(
            llm=LiteLLM(model_name=model_name),  # type: ignore[arg-type]
            prompt="\n".join(pydantic_ai_agent._system_prompts),
            tools=[tool.function for _, tool in pydantic_ai_agent._function_tools.items()],
            mcp_servers=cast(list[MCPServer], mcp_servers),
        )

    def to_tool(self, name: str | None = None, description: str | None = None) -> Tool:
        """
        Convert the agent into a Tool instance.

        Args:
            name: Optional override for the tool name.
            description: Optional override for the tool description.

        Returns:
            Tool instance representing the agent.
        """
        return Tool.from_agent(self, name=name or self.name, description=description or self.description)

    @staticmethod
    def _make_prompt_class_for_agent_subclass(agent_cls: type["Agent[Any, Any, Any]"]) -> type[Prompt] | None:
        system = getattr(agent_cls, "system_prompt", None)
        if not system:
            raise ValueError(f"Agent {agent_cls.__name__} has no system_prompt")
        user = getattr(agent_cls, "user_prompt", "{{ input }}")

        input_type: type[BaseModel] | None = getattr(agent_cls, "input_type", None)
        if input_type is None:
            raise ValueError(f"Agent {agent_cls.__name__} cannot build a Prompt without input_type")

        base_generic = Prompt
        base = base_generic[input_type]

        attrs = {
            "system_prompt": system,
            "user_prompt": user,
        }

        return types.new_class(
            f"_{agent_cls.__name__}Prompt",
            (base,),
            exec_body=lambda ns: ns.update(attrs),
        )

    @overload
    @staticmethod
    def prompt_config(
        input_model: type[_Input],
    ) -> Callable[[type[Any]], type["Agent[LLMOptions, _Input, str]"]]: ...
    @overload
    @staticmethod
    def prompt_config(
        input_model: type[_Input],
        output_model: type[_Output],
    ) -> Callable[[type[Any]], type["Agent[LLMOptions, _Input, _Output]"]]: ...
    @staticmethod
    def prompt_config(
        input_model: type[_Input],
        output_model: type[_Output] | type[NotGiven] = NotGiven,
    ) -> Callable[[type[Any]], type["Agent[LLMOptions, _Input, _Output]"]]:
        """
        Decorator to bind both input and output types of an Agent subclass, with runtime checks.

        Raises:
            TypeError: if the decorated class is not a subclass of Agent,
                       or if input_model is not a Pydantic BaseModel.
        """
        if not isinstance(input_model, type) or not issubclass(input_model, BaseModel):
            raise TypeError(f"input_model must be a subclass of pydantic.BaseModel, got {input_model}")

        if not isinstance(output_model, type):
            raise TypeError(f"output_model must be a type, got {output_model}")

        def decorator(cls: type[Any]) -> type["Agent[LLMOptions, _Input, _Output]"]:
            if not isinstance(cls, type) or not issubclass(cls, Agent):
                raise TypeError(f"Can only decorate subclasses of Agent, got {cls}")

            cls.input_type = input_model
            cls.prompt_cls = Agent._make_prompt_class_for_agent_subclass(cls)

            return cast(type["Agent[LLMOptions, _Input, _Output]"], cls)

        return decorator
