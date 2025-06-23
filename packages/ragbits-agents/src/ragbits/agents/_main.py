from collections.abc import AsyncGenerator, AsyncIterator, Callable
from dataclasses import dataclass
from inspect import iscoroutinefunction
from types import ModuleType, SimpleNamespace
from typing import Any, ClassVar, Generic, cast, overload

from ragbits import agents
from ragbits.agents.exceptions import (
    AgentInvalidPromptInputError,
    AgentToolExecutionError,
    AgentToolNotAvailableError,
    AgentToolNotSupportedError,
)
from ragbits.core.audit.traces import trace
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata, ToolCall
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
    id: str
    name: str
    arguments: dict
    result: Any


@dataclass
class AgentResult(Generic[PromptOutputT]):
    """
    Result of the agent run.
    """

    content: PromptOutputT
    """The output content of the LLM."""
    metadata: dict
    """The additional data returned by the LLM."""
    tool_calls: list[ToolCallResult] | None = None
    """Tool calls run by the Agent."""
    history: ChatFormat | None = None
    """The history of the agent."""

class AgentResultStreaming(AsyncIterator[str | ToolCall | ToolCallResult]):
    """
    An async iterator that collects all yielded items.

    This object is returned by methods like `run_streaming`. It can be used
    in an `async for` loop to process items as they arrive. After the
    loop completes, the `collected` attribute holds a list of all items
    that were yielded.
    """
    def __init__(self, generator: AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace]):
        self._generator = generator
        self.content = ""
        self.tool_calls : list[ToolCallResult] = []
        self.metadata: dict = {}

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
                    self.tool_calls.append(item)
                case SimpleNamespace():
                    item.results = AgentResult(
                        content=self.content,
                        metadata=self.metadata,
                        tool_calls=self.tool_calls,
                    )
                    raise StopAsyncIteration
                case _:
                    raise ValueError(f"Unexpected item: {item}")
            return item
        except StopAsyncIteration:
            raise

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
    Agent class that orchestrates the LLM and the prompt, and can call tools

    Current implementation is highly experimental, and the API is subject to change.
    """

    options_cls: type[AgentOptions] = AgentOptions
    default_module: ClassVar[ModuleType | None] = agents
    configuration_key: ClassVar[str] = "agent"
    
    #! Should we have a method to compress the history, expect compressor object here or in this method (?)
    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        prompt: str | type[Prompt[PromptInputT, PromptOutputT]] | None = None,
        *,
        history: ChatFormat | None = None,
        keep_history: bool = False,
        tools: list[Callable] | None = None,
        default_options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> None:
        # this is misleading - prompt here can be either a system_message, or prompt_type, it has to do nothing with a true prompt that goes to the LLM
        # Why don't we create two separate attributes: promp_type and system_message, both optional?
        # additionally I can get history here -  Does the history define the prompt? - Not necessarily. 
        # But if I get the history and a prompt and have keep history set to True - I need to 
        """
        Initialize the agent instance.

        Args:
            llm: The LLM to run the agent.
            prompt: The prompt for the agent. Can be:
                - str: A string prompt that will be used as system message when combined with string input,
                    or as the user message when no input is provided during run().
                - type[Prompt]: A structured prompt class that will be instantiated with the input.
                - None: No predefined prompt. The input provided to run() will be used as the complete prompt.
            tools: The tools available to the agent.
            default_options: The default options for the agent run.
        """
        super().__init__(default_options)
        self.llm = llm
        self.prompt = prompt
        self.tools_mapping = {} if not tools else {f.__name__: f for f in tools}
        self.history = history
        self.keep_history = keep_history

    async def _execute_tool(self, tool_call: ToolCall) -> ToolCallResult:
        if tool_call.type != "function":
            raise AgentToolNotSupportedError(tool_call.type)

        if tool_call.name not in self.tools_mapping:
            raise AgentToolNotAvailableError(tool_call.name)

        tool = self.tools_mapping[tool_call.name]

        try:
            tool_output = (
                await tool(**tool_call.arguments) if iscoroutinefunction(tool) else tool(**tool_call.arguments)
            )
        except Exception as e:
            raise AgentToolExecutionError(tool_call.name, e) from e
        
        return ToolCallResult(
            id=tool_call.id,
            name=tool_call.name,
            arguments=tool_call.arguments,
            result=tool_output,
        )

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
        input: None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResult[PromptOutputT]: ...

    async def run(self, input : str | PromptInputT | None = None, options : AgentOptions[LLMClientOptionsT] | None = None) -> AgentResult[PromptOutputT]:
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
        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        # How to handle situation if this is not the 1st interaction?
        prompt = self._create_prompt(input)
        tool_calls = []

        if self.history:
            #Ton of things can happen here.
            #1. Someone provided a str - which is considered a system message and a history - what to do then? This combination shouldn't be supported IMO.
            #2. Someone provided a PromptType - which also can get a system message and a history...
            prompt = SimplePrompt(self.history + prompt.chat)

        print(prompt.chat)

        with trace(input=input, options=merged_options) as outputs:
            while True:
                response = cast(
                    LLMResponseWithMetadata[PromptOutputT],
                    await self.llm.generate_with_metadata(
                        prompt=prompt,
                        tools=list(self.tools_mapping.values()),    
                        options=llm_options,
                    ),
                )
                if not response.tool_calls:
                    break

                for tool_call in response.tool_calls:
                    result = await self._execute_tool(tool_call)

                    tool_calls.append(result)

                    # I wonder if this should be on us or on the user?
                    # What in scenario if someone want to evaluate the tool output and do some logic based on it?
                    # So maybe this should be an iterator too?
                    prompt = prompt.add_tool_use_message(**result.__dict__)

            outputs.result = {
                "content": response.content,
                "metadata": response.metadata,
                "tool_calls": tool_calls or None,
            }

            if self.keep_history:
                # But now here shouldn't we add user message and response to the history too?
                # Also with the history, every prompt may be very different.
                prompt = prompt.add_assistant_message(response.content)
                self.history = prompt.chat

            return AgentResult(
                content=response.content,
                metadata=response.metadata,
                tool_calls=tool_calls or None,
                history=self.history,
            )

    def _create_prompt(self, input: PromptInputT) -> SimplePrompt | Prompt[PromptInputT, PromptOutputT]:
        #! Doesn't this break possibility of handling Agent History?
        # Because we do create a new prompt instance for each run?
        # This is just for the runs where keep_history is False.
        if isinstance(self.prompt, type) and issubclass(self.prompt, Prompt):
            return self.prompt(input)
        elif isinstance(self.prompt, str) and isinstance(input, str):
            return SimplePrompt(
                [
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": input},
                ]
            )
        elif isinstance(self.prompt, str) and input is None:
            return SimplePrompt(self.prompt)
        elif isinstance(input, str):
            return SimplePrompt(input)
        else:
            raise AgentInvalidPromptInputError(self.prompt, input)

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, None, str]",
        input: str,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResultStreaming: ...

    @overload
    def run_streaming(
        self: "Agent[LLMClientOptionsT, None, PromptOutputT]",
        input: None = None,
        options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> AgentResultStreaming: ...

    def run_streaming(
        self, input : str | PromptInputT | None = None, options : AgentOptions[LLMClientOptionsT] | None = None
    ) -> AgentResultStreaming:
        """
        Run the agent and streams the output.

        This method returns a `StreamingResult` object that can be asynchronously
        iterated over. After iteration is complete, the `collected` attribute
        of the returned object will contain all the yielded chunks.

        Args:
            input: The input for the agent run.
            options: The options for the agent run.

        Returns:
            A `StreamingResult` object for iteration and collection.
        """
        generator = self._stream_internal(input, options)
        return AgentResultStreaming(generator)

    async def _stream_internal(
        self, input : str | PromptInputT | None = None, options : AgentOptions[LLMClientOptionsT] | None = None
    ) -> AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace]:
        input = cast(PromptInputT, input)
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None

        prompt = self._create_prompt(input)

        with trace(input=input, options=merged_options) as outputs:
            while True:
                returned_tool_call = False
                async for chunk in self.llm.generate_streaming(
                    prompt=prompt,
                    tools=list(self.tools_mapping.values()),
                    options=llm_options,
                ):
                    yield chunk

                    if isinstance(chunk, ToolCall):
                        yield chunk
                        result = await self._execute_tool(chunk)
                        yield result
                        prompt = prompt.add_tool_use_message(**result.__dict__)
                        returned_tool_call = True

                if not returned_tool_call:
                    break

            yield prompt
            yield outputs