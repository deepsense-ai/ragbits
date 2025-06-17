from collections.abc import Callable
from dataclasses import dataclass
from inspect import iscoroutinefunction
from types import ModuleType
from typing import Any, ClassVar, Generic, cast, overload

from ragbits import agents
from ragbits.agents.exceptions import AgentToolNotAvailableError, AgentToolNotSupportedError
from ragbits.core.audit.traces import trace
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata
from ragbits.core.options import Options
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT_co
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
class AgentResult(Generic[PromptOutputT_co]):
    """
    Result of the agent run.
    """

    content: PromptOutputT_co
    """The output content of the LLM."""
    metadata: dict
    """The additional data returned by the LLM."""
    tool_calls: list[ToolCallResult] | None = None
    """Tool calls run by the Agent."""


class AgentOptions(Options, Generic[LLMClientOptionsT]):
    """
    Options for the agent run.
    """

    llm_options: LLMClientOptionsT | None | NotGiven = NOT_GIVEN
    """The options for the LLM."""


class Agent(
    ConfigurableComponent[AgentOptions[LLMClientOptionsT]], Generic[LLMClientOptionsT, PromptInputT, PromptOutputT_co]
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
        prompt: type[Prompt[PromptInputT, PromptOutputT_co]],
        *,
        tools: list[Callable] | None = None,
        default_options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> None:
        """
        Initialize the agent instance.

        Args:
            llm: The LLM to use.
            prompt: The prompt to use.
            tools: The tools available to the agent.
            default_options: The default options for the agent run.
        """
        super().__init__(default_options)
        self.llm = llm
        self.prompt = prompt
        self.tools_mapping = {} if not tools else {f.__name__: f for f in tools}

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT_co]",
        input: PromptInputT,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT_co]: ...

    @overload
    async def run(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT_co]",
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT_co]: ...

    async def run(self, *args: Any, **kwargs: Any) -> AgentResult[PromptOutputT_co]:
        """
        Run the agent. The method is experimental, inputs and outputs may change in the future.

        Args:
            *args: Positional arguments corresponding to the overload signatures.
                - If provided, the first positional argument is interpreted as `input`.
                - If a second positional argument is provided, it is interpreted as `options`.
            **kwargs: Keyword arguments corresponding to the overload signatures.
                - `input`: The input for the agent run.
                - `options`: The options for the agent run.

        Returns:
            The result of the agent run.

        Raises:
            AgentToolNotSupportedError: If the selected tool type is not supported.
            AgentToolNotAvailableError: If the selected tool is not available.
        """
        input = cast(PromptInputT, args[0] if args else kwargs.get("input"))
        options = args[1] if len(args) > 1 else kwargs.get("options")

        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        prompt = self.prompt(input)
        tool_calls = []

        with trace(input=input, options=merged_options) as outputs:
            while True:
                response = cast(
                    LLMResponseWithMetadata[PromptOutputT_co],
                    await self.llm.generate_with_metadata(
                        prompt=prompt,
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
                    prompt = prompt.add_tool_use_message(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        tool_arguments=tool_call.arguments,
                        tool_call_result=tool_output,
                    )

            outputs.result = AgentResult(
                content=response.content,
                metadata=response.metadata,
                tool_calls=tool_calls or None,
            )
            return outputs.result

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
