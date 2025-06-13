from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from inspect import iscoroutinefunction
from types import ModuleType
from typing import Any, ClassVar, Generic, cast, overload

from ragbits import agents
from ragbits.agents.exceptions import AgentNotAvailableToolSelectedError, AgentNotSupportedToolInResponseError
from ragbits.core.llms.base import LLM, LLMClientOptionsT, ToolCall
from ragbits.core.options import Options
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent


@dataclass
class AgentResult(Generic[PromptOutputT]):
    """
    Result of the agent run.
    """

    content: PromptOutputT | str
    """The output content of the LLM."""
    metadata: dict
    """The additional data returned by the LLM."""
    tool_call: ToolCall | None = None
    """Tool call returned by the LLM."""
    tool_call_result: str | None = None
    """Result of tool call returned by the LLM."""


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
        prompt: type[Prompt[PromptInputT, PromptOutputT]],
        *,
        default_options: AgentOptions[LLMClientOptionsT] | None = None,
        tools: list[Callable] | None = None,
    ) -> None:
        """
        Initialize the agent instance.

        Args:
            llm: The LLM to use.
            prompt: The prompt to use.
            default_options: The default options for the agent run.
            tools: Functions to be used as tools by LLM.
        """
        super().__init__(default_options)
        self.llm = llm
        self.prompt = prompt
        self.tools_mapping = {} if not tools else {f.__name__: f for f in tools}

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

    async def run(self, *args: Any, **kwargs: Any) -> AgentResult[PromptOutputT]:  # noqa: D417
        """
        Run the agent. The method is experimental, inputs and outputs may change in the future.

        Args:
            input: The input for the agent run.
            options: The options for the agent run.

        Returns:
            The result of the agent run.
        """
        input = cast(PromptInputT, args[0] if args else kwargs.get("input"))
        options = args[1] if len(args) > 1 else kwargs.get("options")

        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        async for _response in self.iter(input, llm_options):
            pass

        return _response

    async def iter(
        self, input: PromptInputT, options: LLMClientOptionsT | None = None
    ) -> AsyncGenerator[AgentResult[PromptOutputT], None]:
        """
        AsyncGenerator object that can be used to iterate over agent responses.

        Args:
             input: The input for the agent run.
             options: The options for the agent run.

        Returns:
            The result of the agent run.
        """
        prompt = self.prompt(input)
        while True:
            response = await self.llm.generate_with_metadata(
                prompt, options=options, tools=list(self.tools_mapping.values())
            )
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    if tool_call.type == "function":
                        if tool_call.name not in self.tools_mapping:
                            raise AgentNotAvailableToolSelectedError(tool_call.name)
                        function_to_call = self.tools_mapping[tool_call.name]
                        if iscoroutinefunction(function_to_call):
                            tool_call_result = await function_to_call(**tool_call.arguments)
                        else:
                            tool_call_result = function_to_call(**tool_call.arguments)
                        prompt = prompt.add_tool_use_message(
                            tool_call.id,
                            tool_call.name,
                            str(tool_call.arguments),
                            str(tool_call_result),
                        )
                    else:
                        raise AgentNotSupportedToolInResponseError(tool_call.type)
                    yield AgentResult(
                        content=response.content,
                        metadata=response.metadata,
                        tool_call=tool_call,
                        tool_call_result=str(tool_call_result),
                    )
            else:
                break
        yield AgentResult(content=response.content, metadata=response.metadata)
