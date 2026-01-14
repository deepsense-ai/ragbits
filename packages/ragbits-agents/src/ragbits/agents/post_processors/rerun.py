from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

from ragbits.agents.post_processors.base import PostProcessor
from ragbits.core.llms.base import LLMClientOptionsT
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentOptions, AgentResult, AgentRunContext


class RerunPostProcessor(PostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """
    Post-processor that conditionally reruns the agent based on a processing function.

    The processing function validates/executes the agent output and returns either:
    - Success data (e.g., list[Row])
    - A Failure object (e.g., SQLFailure) that triggers a rerun

    This replaces patterns like Pydantic AI's ModelRetry mechanism.
    """

    def __init__(
        self,
        process_fn: Callable[["AgentResult[PromptOutputT]"], Any],
        failure_type: type,
        rerun_input_fn: Callable[[Any, int], str],
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the RerunPostProcessor.

        Args:
            process_fn: Function that processes the AgentResult and returns either success data
                or a failure object. This function does the actual validation/execution.
            failure_type: The type that indicates failure (e.g., SQLFailure). If process_fn returns
                an instance of this type, a rerun is triggered.
            rerun_input_fn: Function to generate rerun input from the failure object.
                Takes (failure_object, attempt_number) and returns a string input.
            max_retries: Maximum number of times to rerun the agent. Defaults to 3.
        """
        self.process_fn = process_fn
        self.failure_type = failure_type
        self.rerun_input_fn = rerun_input_fn
        self.max_retries = max_retries

    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        options: Optional["AgentOptions[LLMClientOptionsT]"] = None,
        context: Optional["AgentRunContext"] = None,
    ) -> "AgentResult[PromptOutputT]":
        """
        Process the agent result and rerun if necessary based on the processing function output.

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
            # Process the output
            processed_output = self.process_fn(current_result)

            # # Cache the processed output in metadata
            # current_result.metadata["_processed_output"] = processed_output

            # Check if it's a failure that needs rerun
            if not isinstance(processed_output, self.failure_type):
                # Success - no rerun needed
                current_result.metadata.setdefault("post_processors", {})["rerun"] = {
                    "rerun_count": rerun_count,
                    "max_retries": self.max_retries,
                }
                if not agent.keep_history:
                    agent.history = []
                current_result.content = processed_output
                return current_result

            # It's a failure - generate rerun input
            rerun_input = self.rerun_input_fn(processed_output, retries)

            # Rerun the agent without post-processors to avoid infinite recursion
            current_result = await agent._run_without_post_processing(rerun_input, options, context)
            retries += 1
            rerun_count += 1

        # Max retries exceeded, process one last time and return
        processed_output = self.process_fn(current_result)
        current_result.metadata["_processed_output"] = processed_output
        current_result.metadata.setdefault("post_processors", {})["rerun"] = {
            "rerun_count": rerun_count,
            "max_retries": self.max_retries,
            "max_retries_exceeded": True,
        }

        if not agent.keep_history:
            agent.history = []

        return current_result
