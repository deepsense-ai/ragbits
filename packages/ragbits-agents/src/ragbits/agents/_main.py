from dataclasses import dataclass
from types import ModuleType
from typing import Any, ClassVar, Generic, cast, overload

from ragbits import agents
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.options import Options
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent


@dataclass
class AgentResult(Generic[PromptOutputT]):
    """
    Result of the agent run.
    """

    content: PromptOutputT
    """The output content of the LLM."""
    metadata: dict
    """The additional data returned by the LLM."""


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
    ) -> None:
        """
        Initialize the agent instance.

        Args:
            llm: The LLM to use.
            prompt: The prompt to use.
            default_options: The default options for the agent run.
        """
        super().__init__(default_options)
        self.llm = llm
        self.prompt = prompt

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

        prompt = self.prompt(input)
        response = await self.llm.generate_with_metadata(prompt, options=llm_options)

        return AgentResult(
            content=response.content,
            metadata=response.metadata,
        )
