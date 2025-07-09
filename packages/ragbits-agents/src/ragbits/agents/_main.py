import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from inspect import iscoroutinefunction
from types import ModuleType, SimpleNamespace
from typing import ClassVar, Generic, cast, overload

from ragbits import agents
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
    AgentMaxTurnsExceededError,
    AgentToolDuplicateError,
    AgentToolExecutionError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.agents.mcp.server import MCPServer
from ragbits.agents.mcp.utils import get_tools
from ragbits.agents.tool import Tool, ToolCallResult
from ragbits.core.audit.traces import trace
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata, ToolCall
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


class AgentOptions(Options, Generic[LLMClientOptionsT]):
    """
    Options for the agent run.
    """

    llm_options: LLMClientOptionsT | None | NotGiven = NOT_GIVEN
    """The options for the LLM."""
    max_turns: int | None | NotGiven = NOT_GIVEN
    """The maximum number of turns the agent can take, if NOT_GIVEN,
    it defaults to 10, if None, agent will run forever"""


class AgentResultStreaming(AsyncIterator[str | ToolCall | ToolCallResult]):
    """
    An async iterator that will collect all yielded items by LLM.generate_streaming(). This object is returned
    by `run_streaming`. It can be used in an `async for` loop to process items as they arrive. After the loop completes,
    all items are available under the same names as in AgentResult class.
    """

    def __init__(self, generator: AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt]):
        self._generator = generator
        self.content: str = ""
        self.tool_calls: list[ToolCallResult] | None = None
        self.metadata: dict = {}
        self.history: ChatFormat

    def __aiter__(self) -> AsyncIterator[str | ToolCall | ToolCallResult]:
        return self

    async def __anext__(self) -> str | ToolCall | ToolCallResult:
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
                case BasePrompt():
                    item.add_assistant_message(self.content)
                    self.history = item.chat
                    item = await self._generator.__anext__()
                    item = cast(SimpleNamespace, item)
                    item.result = {
                        "content": self.content,
                        "metadata": self.metadata,
                        "tool_calls": self.tool_calls,
                    }
                    raise StopAsyncIteration
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
    ) -> AgentResult[PromptOutputT]: ...

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    async def run(
        self, input: str | PromptInputT | None = None, options: AgentOptions[LLMClientOptionsT] | None = None
    ) -> AgentResult[PromptOutputT]:
        """
        Run the agent. The method is experimental, inputs and outputs may change in the future.

        Args:
            input: The input for the agent run. Can be:
                - str: A string input that will be used as user message.
                - PromptInputT: Structured input for use with structured prompt classes.
                - None: No input. Only valid when a string prompt was provided during initialization.
            options: The options for the agent run.

        Returns:
            The result of the agent run.

        Raises:
            AgentToolDuplicateError: If the tool names are duplicated.
            AgentToolNotSupportedError: If the selected tool type is not supported.
            AgentToolNotAvailableError: If the selected tool is not available.
            AgentInvalidPromptInputError: If the prompt/input combination is invalid.
            AgentMaxTurnsExceededError: If the maximum number of turns is exceeded.
        """
        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        prompt_with_history = self._get_prompt_with_history(input)
        tools_mapping = await self._get_all_tools()
        tool_calls = []

        turn_count = 0
        max_turns = merged_options.max_turns
        max_turns = 10 if max_turns is NOT_GIVEN else max_turns
        with trace(input=input, options=merged_options) as outputs:
            while not max_turns or turn_count < max_turns:
                response = cast(
                    LLMResponseWithMetadata[PromptOutputT],
                    await self.llm.generate_with_metadata(
                        prompt=prompt_with_history,
                        tools=[tool.to_function_schema() for tool in tools_mapping.values()],
                        options=llm_options,
                    ),
                )
                if not response.tool_calls:
                    break

                for tool_call in response.tool_calls:
                    result = await self._execute_tool(tool_call=tool_call, tools_mapping=tools_mapping)
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
            )

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str | None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResultStreaming: ...

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResultStreaming: ...

    def run_streaming(
        self, input: str | PromptInputT | None = None, options: AgentOptions[LLMClientOptionsT] | None = None
    ) -> AgentResultStreaming:
        """
        This method returns an `AgentResultStreaming` object that can be asynchronously
        iterated over. After the loop completes, all items are available under the same names as in AgentResult class.

        Args:
            input: The input for the agent run.
            options: The options for the agent run.

        Returns:
            A `StreamingResult` object for iteration and collection.

        Raises:
            AgentToolDuplicateError: If the tool names are duplicated.
            AgentToolNotSupportedError: If the selected tool type is not supported.
            AgentToolNotAvailableError: If the selected tool is not available.
            AgentInvalidPromptInputError: If the prompt/input combination is invalid.
            AgentMaxTurnsExceededError: If the maximum number of turns is exceeded.
        """
        generator = self._stream_internal(input, options)
        return AgentResultStreaming(generator)

    async def _stream_internal(
        self, input: str | PromptInputT | None = None, options: AgentOptions[LLMClientOptionsT] | None = None
    ) -> AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt]:
        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        prompt_with_history = self._get_prompt_with_history(input)
        tools_mapping = await self._get_all_tools()
        turn_count = 0
        max_turns = merged_options.max_turns
        max_turns = 10 if max_turns is NOT_GIVEN else max_turns
        with trace(input=input, options=merged_options) as outputs:
            while not max_turns or turn_count < max_turns:
                returned_tool_call = False
                async for chunk in self.llm.generate_streaming(
                    prompt=prompt_with_history,
                    tools=[tool.to_function_schema() for tool in tools_mapping.values()],
                    options=llm_options,
                ):
                    yield chunk

                    if isinstance(chunk, ToolCall):
                        result = await self._execute_tool(tool_call=chunk, tools_mapping=tools_mapping)
                        yield result
                        prompt_with_history = prompt_with_history.add_tool_use_message(**result.__dict__)
                        returned_tool_call = True
                turn_count += 1

                if not returned_tool_call:
                    break
            else:
                raise AgentMaxTurnsExceededError(cast(int, max_turns))

            yield prompt_with_history
            if self.keep_history:
                self.history = prompt_with_history.chat
            yield outputs

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
    async def _execute_tool(tool_call: ToolCall, tools_mapping: dict[str, Tool]) -> ToolCallResult:
        if tool_call.type != "function":
            raise AgentToolNotSupportedError(tool_call.type)

        if tool_call.name not in tools_mapping:
            raise AgentToolNotAvailableError(tool_call.name)

        tool = tools_mapping[tool_call.name]

        try:
            tool_output = (
                await tool.on_tool_call(**tool_call.arguments)
                if iscoroutinefunction(tool.on_tool_call)
                else tool.on_tool_call(**tool_call.arguments)
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
        Extract agent skills from all available tools.

        Returns:
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
