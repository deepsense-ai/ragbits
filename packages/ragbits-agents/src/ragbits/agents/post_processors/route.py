from typing import TYPE_CHECKING, Callable, Optional

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
        input_fn: Optional[Callable[["AgentResult[PromptOutputT]"], str]] = None,
        combine_results: bool = False,
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
        """
        self.target_agent = target_agent
        self.input_fn = input_fn
        self.combine_results = combine_results

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
            The result after routing to the target agent.
        """
        # Prepare input for target agent
        if self.input_fn:
            target_input = self.input_fn(result)
        else:
            target_input = result.content

        # Route to target agent
        routed_result = await self.target_agent.run(target_input, options=options, context=context)

        # Combine or replace results
        if self.combine_results:
            combined_content = f"{result.content}\n\n--- Routed Agent Output ---\n\n{routed_result.content}"
            result.content = combined_content
            result.metadata.setdefault("post_processors", {})["route"] = {
                "target_agent": self.target_agent.name or self.target_agent.id,
                "original_length": len(str(result.content)),
                "routed_length": len(str(routed_result.content)),
                "combined": True,
            }
            return result
        else:
            # Return the routed result but preserve original metadata
            routed_result.metadata.setdefault("post_processors", {})["route"] = {
                "source_agent": agent.name or agent.id,
                "target_agent": self.target_agent.name or self.target_agent.id,
                "original_content": result.content,
                "original_length": len(str(result.content)),
                "routed_length": len(str(routed_result.content)),
            }
            return routed_result
