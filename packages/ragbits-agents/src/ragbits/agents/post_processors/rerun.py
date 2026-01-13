from typing import TYPE_CHECKING, Callable, Optional

from ragbits.agents.post_processors.base import PostProcessor
from ragbits.core.llms.base import LLMClientOptionsT
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentOptions, AgentResult, AgentRunContext


class RerunPostProcessor(PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """
    Post-processor that conditionally reruns the agent based on custom validation logic.

    This allows flexible rerun behavior where you can define your own condition function
    to determine whether the agent should be rerun, and optionally modify the input
    for the rerun.
    """

    def __init__(
        self,
        should_rerun: Callable[["AgentResult[PromptOutputT]"], bool],
        max_retries: int = 3,
        rerun_input_fn: Optional[Callable[["AgentResult[PromptOutputT]", int], str]] = None,
    ) -> None:
        """
        Initialize the RerunPostProcessor.

        Args:
            should_rerun: Function that takes an AgentResult and returns True if rerun is needed.
            max_retries: Maximum number of times to rerun the agent. Defaults to 3.
            rerun_input_fn: Optional function to generate rerun input. Takes (result, attempt_number)
                and returns a string input. If None, uses the original result content as input.
        """
        self.should_rerun = should_rerun
        self.max_retries = max_retries
        self.rerun_input_fn = rerun_input_fn

    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        options: Optional["AgentOptions[LLMClientOptionsT]"] = None,
        context: Optional["AgentRunContext"] = None,
    ) -> "AgentResult[PromptOutputT]":
        """
        Process the agent result and rerun if necessary based on the condition.

        Args:
            result: The agent result to process.
            agent: The agent instance.
            options: Optional agent options.
            context: Optional agent run context.

        Returns:
            The final agent result after processing and potential reruns.
        """
        retries = 0
        current_result = result
        rerun_count = 0
        agent.history = result.history

        while retries < self.max_retries:
            if not self.should_rerun(current_result):
                # Attach metadata about reruns
                current_result.metadata.setdefault("post_processors", {})["rerun"] = {
                    "rerun_count": rerun_count,
                    "max_retries": self.max_retries,
                }
                if not agent.keep_history:
                    agent.history = []
                return current_result

            # Prepare input for rerun
            if self.rerun_input_fn:
                rerun_input = self.rerun_input_fn(current_result, retries)
            else:
                rerun_input = f"Previous attempt was not satisfactory. Please try again.\n\nPrevious output: {current_result.content}"

            # Rerun the agent without post-processors to avoid infinite recursion
            current_result = await agent._run_without_post_processing(rerun_input, options, context)
            retries += 1
            rerun_count += 1

        # Max retries exceeded, return last result with metadata
        current_result.metadata.setdefault("post_processors", {})["rerun"] = {
            "rerun_count": rerun_count,
            "max_retries": self.max_retries,
            "max_retries_exceeded": True,
        }

        if not agent.keep_history:
            agent.history = []

        return current_result
