from abc import ABC
from types import SimpleNamespace
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel

from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms.base import LLMOptions, ToolCall, Usage
from ragbits.core.prompt.base import BasePrompt

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentResult


LLMOpts = TypeVar("LLMOpts", bound=LLMOptions)
PromptIn = TypeVar("PromptIn", bound=BaseModel | None)
PromptOut = TypeVar("PromptOut")


class BasePostProcessor(ABC, Generic[LLMOpts, PromptIn, PromptOut]):
    """Base class for post-processors."""

    @property
    def supports_streaming(self) -> bool:
        """
        Whether this post-processor supports streaming mode.

        If True, the processor can work with partial content during streaming
        via process_streaming() method.

        If False, the processor will only be called after streaming is complete
        with the full result via process() method.
        """
        return False

    async def process(  # noqa: PLR6301
        self,
        result: "AgentResult[PromptOut]",
        agent: "Agent[LLMOpts, PromptIn, PromptOut]",
    ) -> "AgentResult[PromptOut]":
        """
        Process the complete agent result (called after streaming is done).

        Args:
            result: The complete AgentResult from the agent or previous post-processor.
            agent: The Agent instance that generated the result. Can be used to re-run
                  the agent with modified input if needed.

        Returns:
            Modified AgentResult to pass to the next processor or return as final result.
        """
        return result

    async def process_streaming(  # noqa: PLR6301
        self,
        chunk: str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage,
        agent: "Agent[LLMOpts, PromptIn, PromptOut]",
    ) -> str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage:
        """
        Process any chunk during streaming (only called if supports_streaming=True).

        Args:
            chunk: The current chunk being streamed.
            agent: The Agent instance generating the content.

        Returns:
            Modified chunk to yield, or None to suppress this chunk.
            Return the same chunk if no modification needed.
        """
        return chunk
