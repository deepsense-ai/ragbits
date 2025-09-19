from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import TYPE_CHECKING, Generic, TypeVar

from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms.base import LLMOptions, ToolCall, Usage
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentResult


LLMOptionsT = TypeVar("LLMOptionsT", bound=LLMOptions)


class BasePostProcessor(Generic[LLMOptionsT, PromptInputT, PromptOutputT]):
    """Base class for post-processors."""

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """
        Whether this post-processor supports streaming mode.

        If True, the processor can work with content during streaming
        via process_streaming() method.

        If False, the processor will only be called after streaming is complete
        with the full result via process() method.
        """


class PostProcessor(ABC, BasePostProcessor[LLMOptionsT, PromptInputT, PromptOutputT]):
    """Base class for non-streaming post-processors."""

    @property
    def supports_streaming(self) -> bool:
        """Whether this post-processor supports streaming mode."""
        return False

    @abstractmethod
    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMOptionsT, PromptInputT, PromptOutputT]",
    ) -> "AgentResult[PromptOutputT]":
        """
        Process the complete agent result.

        Args:
            result: The complete AgentResult from the agent or previous post-processor.
            agent: The Agent instance that generated the result. Can be used to re-run
                  the agent with modified input if needed.

        Returns:
            Modified AgentResult to pass to the next processor or return as final result.
        """


class StreamingPostProcessor(ABC, BasePostProcessor[LLMOptionsT, PromptInputT, PromptOutputT]):
    """Base class for streaming post-processors."""

    @property
    def supports_streaming(self) -> bool:
        """Whether this post-processor supports streaming mode."""
        return True

    @abstractmethod
    async def process_streaming(
        self,
        chunk: str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage,
        agent: "Agent[LLMOptionsT, PromptInputT, PromptOutputT]",
    ) -> str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage:
        """
        Process chunks during streaming.

        Args:
            chunk: The current chunk being streamed.
            agent: The Agent instance generating the content.

        Returns:
            Modified chunk to yield, or None to suppress this chunk.
            Return the same chunk if no modification needed.
        """
