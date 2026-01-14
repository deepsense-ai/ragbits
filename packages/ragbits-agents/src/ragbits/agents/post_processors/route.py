from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from ragbits.agents.post_processors.base import PostProcessor
from ragbits.core.llms.base import LLMClientOptionsT
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentOptions, AgentResult, AgentRunContext


class RoutePostProcessor(PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """
    Post-processor that routes agent output to another specified agent for additional processing.

    This enables multi-agent workflows where one agent's output is passed to another agent
    for further refinement, summarization, translation, or any other transformation.
    """

    def __init__(
        self,
        target_agent: "Agent",
        input_fn: Callable[["AgentResult[PromptOutputT]"], str] | None = None,
        combine_results: bool = False,
        should_route: Callable[["AgentResult[PromptOutputT]"], bool] | None = None,
    ) -> None:
        """
        Initialize the RoutePostProcessor.

        Args:
            target_agent: The agent to route the output to.
            input_fn: Optional function to generate input for the target agent.
                Takes the current AgentResult and returns a string input.
                If None, uses the result content directly.
            combine_results: If True, combines the original and routed results.
                If False, returns only the routed result. Defaults to False.
            should_route: Optional function to determine if routing should occur.
                Takes the current AgentResult and returns True if routing should happen.
                If None, always routes. Defaults to None.
        """
        self.target_agent = target_agent
        self.input_fn = input_fn
        self.combine_results = combine_results
        self.should_route = should_route

    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        options: Optional["AgentOptions[LLMClientOptionsT]"] = None,
        context: Optional["AgentRunContext"] = None,
    ) -> "AgentResult[PromptOutputT]":
        """
        Route the agent result to the target agent for processing.

        Args:
            result: The agent result to process.
            agent: The agent instance.
            options: Optional agent options.
            context: Optional agent run context.

        Returns:
            The result after routing to the target agent, or the original result if routing is skipped.
        """
        # Check if we should route
        if self.should_route and not self.should_route(result):
            # Skip routing - return original result
            return result

        # Prepare input for target agent
        target_input = self.input_fn(result) if self.input_fn else result.content

        # Route to target agent
        routed_result = await self.target_agent.run(target_input, options=options, context=context)

        # Combine or replace results
        if self.combine_results:
            combined_content = f"{result.content}\n\n--- Routed Agent Output ---\n\n{routed_result.content}"
            result.content = combined_content  # type: ignore[assignment]
        result.metadata.setdefault("post_processors", {})["route"] = {
            "target_agent": self.target_agent.name or self.target_agent.id,
        }
        return result
