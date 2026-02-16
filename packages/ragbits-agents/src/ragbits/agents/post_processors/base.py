from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import TYPE_CHECKING, Generic

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms.base import LLMClientOptionsT, ToolCall, Usage
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent


class StreamingPostProcessor(ABC, Generic[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """Base class for streaming post-processors."""

    @abstractmethod
    async def process_streaming(
        self,
        chunk: str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest,
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
    ) -> str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest:
        """
        Process chunks during streaming.

        Args:
            chunk: The current chunk being streamed.
            agent: The Agent instance generating the content.

        Returns:
            Modified chunk to yield, or None to suppress this chunk.
            Return the same chunk if no modification needed.
        """


async def stream_with_post_processing(
    generator: AsyncGenerator[
        str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest, None
    ],
    post_processors: list[StreamingPostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]],
    agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
) -> AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest, None]:
    """
    Stream with support for streaming post-processors.

    Each streaming processor processes chunks in real-time via process_streaming().
    """
    async for chunk in generator:
        processed_chunk = chunk
        for streaming_processor in post_processors:
            processed_chunk = await streaming_processor.process_streaming(chunk=processed_chunk, agent=agent)
            if processed_chunk is None:
                break

        if processed_chunk is not None:
            yield processed_chunk
