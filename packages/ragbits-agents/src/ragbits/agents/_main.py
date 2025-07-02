from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from inspect import getdoc, iscoroutinefunction
from types import ModuleType
from typing import Any, ClassVar, Generic, cast, overload

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from ragbits import agents
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.core.audit.traces import trace
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata
from ragbits.core.options import Options
from ragbits.core.prompt.base import ChatFormat, SimplePrompt
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent


@dataclass
class ToolCallResult:
    """
    Result of the tool call.
    """

    name: str
    arguments: dict
    output: Any


@dataclass
class AgentResult(Generic[PromptOutputT]):
    """
    Result of the agent run.
    """

    content: PromptOutputT
    """The output content of the LLM."""
    metadata: dict
    """The additional data returned by the LLM."""
    history: ChatFormat
    """The history of the agent."""
    tool_calls: list[ToolCallResult] | None = None
    """Tool calls run by the Agent."""


class AgentOptions(Options, Generic[LLMClientOptionsT]):
    """
    Options for the agent run.
    """

    llm_options: LLMClientOptionsT | None | NotGiven = NOT_GIVEN
    """The options for the LLM."""


class Agent(
    ConfigurableComponent[AgentOptions[LLMClientOptionsT]], Generic[LLMClientOptionsT, PromptInputT, PromptOutputT]
):
    """
    Agent class that orchestrates the LLM and the prompt.

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
            default_options: The default options for the agent run.
        """
        super().__init__(default_options)
        self.llm = llm
        self.prompt = prompt
        self.tools_mapping = {} if not tools else {f.__name__: f for f in tools}
        self.history = history or []
        self.keep_history = keep_history

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: str,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    async def run(self, *args: Any, **kwargs: Any) -> AgentResult[PromptOutputT]:
        """
        Run the agent. The method is experimental, inputs and outputs may change in the future.

        Args:
            *args: Positional arguments corresponding to the overload signatures.
                - If provided, the first positional argument is interpreted as `input`.
                - If a second positional argument is provided, it is interpreted as `options`.
            **kwargs: Keyword arguments corresponding to the overload signatures.
                - `input`: The input for the agent run. Can be:
                  - str: A string input that will be used as user message.
                  - PromptInputT: Structured input for use with structured prompt classes.
                  - None: No input. Only valid when a string prompt was provided during initialization.
                - `options`: The options for the agent run.

        Returns:
            The result of the agent run.

        Raises:
            AgentToolNotSupportedError: If the selected tool type is not supported.
            AgentToolNotAvailableError: If the selected tool is not available.
            AgentInvalidPromptInputError: If the prompt/input combination is invalid.
        """
        input = cast(PromptInputT, args[0] if args else kwargs.get("input"))
        options = args[1] if len(args) > 1 else kwargs.get("options")

        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        prompt_with_history = self._get_prompt_with_history(input)
        tool_calls = []

        with trace(input=input, options=merged_options) as outputs:
            while True:
                response = cast(
                    LLMResponseWithMetadata[PromptOutputT],
                    await self.llm.generate_with_metadata(
                        prompt=prompt_with_history,
                        tools=list(self.tools_mapping.values()),
                        options=llm_options,
                    ),
                )
                if not response.tool_calls:
                    break

                for tool_call in response.tool_calls:
                    if tool_call.type != "function":
                        raise AgentToolNotSupportedError(tool_call.type)

                    if tool_call.name not in self.tools_mapping:
                        raise AgentToolNotAvailableError(tool_call.name)

                    tool = self.tools_mapping[tool_call.name]
                    tool_output = (
                        await tool(**tool_call.arguments) if iscoroutinefunction(tool) else tool(**tool_call.arguments)
                    )
                    tool_calls.append(
                        ToolCallResult(
                            name=tool_call.name,
                            arguments=tool_call.arguments,
                            output=tool_output,
                        )
                    )
                    prompt_with_history = prompt_with_history.add_tool_use_message(
                        id=tool_call.id,
                        name=tool_call.name,
                        arguments=tool_call.arguments,
                        result=tool_output,
                    )

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

    def _get_prompt_with_history(self, input: PromptInputT) -> SimplePrompt | Prompt[PromptInputT, PromptOutputT]:
        curr_history = deepcopy(self.history)
        if isinstance(self.prompt, type) and issubclass(self.prompt, Prompt):
            # If we had actual instance we could just run add_user_message here
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

    def get_agent_card(
        self,
        name: str,
        description: str,
        version: str = "0.0.0",
        host: str = "127.0.0.1",
        port: str = "8000",
        protocol: str = "http",
        default_input_modes: list[str] | None = None,
        default_output_modes: list[str] | None = None,
        capabilities: AgentCapabilities | None = None,
        skills: list[AgentSkill] | None = None,
    ) -> AgentCard:
        """
        Creates an AgentCard that encapsulates metadata about the agent,
        such as its name, version, description, network location, supported input/output modes,
        capabilities, and skills.

        Args:
            name: Human-readable name of the agent.
            description: A brief description of the agent.
            version: Version string of the agent. Defaults to "0.0.0".
            host: Hostname or IP where the agent will be served. Defaults to "0.0.0.0".
            port: Port number on which the agent listens. Defaults to "8000".
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
            skills=skills or [self._extract_agent_skill(f) for f in self.tools_mapping.values()],
            capabilities=capabilities or AgentCapabilities(),
        )

    @staticmethod
    def _extract_agent_skill(func: Callable) -> AgentSkill:
        """
        Extracts an AgentSkill description from a given callable.
        Uses the function name and its docstring to populate the skill's metadata.

        Args:
            func: The function to extract skill information from.

        Returns:
            The skill representation with name, id, description, and tags.
        """
        doc = getdoc(func) or ""
        return AgentSkill(name=func.__name__.replace("_", " ").title(), id=func.__name__, description=doc, tags=[])

    # TODO: implement run_streaming method according to the comment - https://github.com/deepsense-ai/ragbits/pull/623#issuecomment-2970514478
    # @overload
    # def run_streaming(
    #     self: "Agent[LLMClientOptionsT, PromptInputT, str]",
    #     input: PromptInputT,
    #     options: AgentOptions[LLMClientOptionsT] | None = None,
    # ) -> AsyncGenerator[str | ToolCall, None]: ...

    # @overload
    # def run_streaming(
    #     self: "Agent[LLMClientOptionsT, None, str]",
    #     options: AgentOptions[LLMClientOptionsT] | None = None,
    # ) -> AsyncGenerator[str | ToolCall, None]: ...

    # async def run_streaming(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str | ToolCall, None]:  # noqa: D417
    #     """
    #     Run the agent. The method is experimental, inputs and outputs may change in the future.

    #     Args:
    #         input: The input for the agent run.
    #         options: The options for the agent run.

    #     Yields:
    #         Response text chunks or tool calls from the Agent.
    #     """
    #     input = cast(PromptInputT, args[0] if args else kwargs.get("input"))
    #     options = args[1] if len(args) > 1 else kwargs.get("options")

    #     merged_options = (self.default_options | options) if options else self.default_options
    #     tools = merged_options.tools or None
    #     llm_options = merged_options.llm_options or None

    #     prompt = self.prompt(input)
    #     tools_mapping = {} if not tools else {f.__name__: f for f in tools}

    #     while True:
    #         returned_tool_call = False
    #         async for chunk in self.llm.generate_streaming(
    #             prompt=prompt,
    #             tools=tools,  # type: ignore
    #             options=llm_options,
    #         ):
    #             yield chunk

    #             if isinstance(chunk, ToolCall):
    #                 if chunk.type != "function":
    #                     raise AgentToolNotSupportedError(chunk.type)

    #                 if chunk.name not in tools_mapping:
    #                     raise AgentToolNotAvailableError(chunk.name)

    #                 tool = tools_mapping[chunk.name]
    #                 tool_output = (
    #                     await tool(**chunk.arguments) if iscoroutinefunction(tool) else tool(**chunk.arguments)
    #                 )

    #                 prompt = prompt.add_tool_use_message(
    #                     tool_call_id=chunk.id,
    #                     tool_name=chunk.name,
    #                     tool_arguments=chunk.arguments,
    #                     tool_call_result=tool_output,
    #                 )
    #                 returned_tool_call = True

    #         if not returned_tool_call:
    #             break
