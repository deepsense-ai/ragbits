from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import TYPE_CHECKING, Generic, Optional, cast

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms.base import LLMClientOptionsT, ToolCall, Usage
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

if TYPE_CHECKING:
    from ragbits.agents._main import Agent, AgentOptions, AgentResult, AgentRunContext


class BasePostProcessor(Generic[LLMClientOptionsT, PromptInputT, PromptOutputT]):
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


class PostProcessor(ABC, BasePostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """Base class for non-streaming post-processors."""

    @property
    def supports_streaming(self) -> bool:
        """Whether this post-processor supports streaming mode."""
        return False

    @abstractmethod
    async def process(
        self,
        result: "AgentResult[PromptOutputT]",
        agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
        options: Optional["AgentOptions[LLMClientOptionsT]"] = None,
        context: Optional["AgentRunContext"] = None,
    ) -> "AgentResult[PromptOutputT]":
        """
        Process the complete agent result.

        Args:
            result: The complete AgentResult from the agent or previous post-processor.
            agent: The Agent instance that generated the result. Can be used to re-run
                  the agent with modified input if needed.
            options: The options for the agent run.
            context: The context for the agent run.

        Returns:
            Modified AgentResult to pass to the next processor or return as final result.
        """


class StreamingPostProcessor(ABC, BasePostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]):
    """Base class for streaming post-processors."""

    @property
    def supports_streaming(self) -> bool:
        """Whether this post-processor supports streaming mode."""
        return True

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
    post_processors: (
        list[StreamingPostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]]
        | list[BasePostProcessor[LLMClientOptionsT, PromptInputT, PromptOutputT]]
    ),
    agent: "Agent[LLMClientOptionsT, PromptInputT, PromptOutputT]",
) -> AsyncGenerator[str | ToolCall | ToolCallResult | SimpleNamespace | BasePrompt | Usage | ConfirmationRequest, None]:
    """
    Stream with support for both streaming and non-streaming post-processors.

    Streaming processors get chunks in real-time via process_streaming().
    Non-streaming processors get the complete result via process().
    """
    from ragbits.agents import AgentResult

    streaming_processors = [p for p in post_processors or [] if isinstance(p, StreamingPostProcessor)]
    non_streaming_processors = [p for p in post_processors or [] if isinstance(p, PostProcessor)]

    accumulated_content = ""
    tool_call_results: list[ToolCallResult] = []
    usage: Usage = Usage()
    prompt_with_history: BasePrompt | None = None

    async for chunk in generator:
        processed_chunk = chunk
        for streaming_processor in streaming_processors:
            processed_chunk = await streaming_processor.process_streaming(chunk=processed_chunk, agent=agent)
            if processed_chunk is None:
                break

        if isinstance(processed_chunk, str):
            accumulated_content += processed_chunk
        elif isinstance(processed_chunk, ToolCallResult):
            tool_call_results.append(processed_chunk)
        elif isinstance(processed_chunk, Usage):
            usage = processed_chunk
        elif isinstance(processed_chunk, BasePrompt):
            prompt_with_history = processed_chunk

        if processed_chunk is not None:
            yield processed_chunk

    if non_streaming_processors and prompt_with_history:
        agent_result = AgentResult(
            content=cast(PromptOutputT, accumulated_content),
            metadata={},
            tool_calls=tool_call_results or None,
            history=prompt_with_history.chat,
            usage=usage,
        )

        current_result = agent_result
        for non_streaming_processor in non_streaming_processors:
            current_result = await non_streaming_processor.process(current_result, agent)

        yield current_result.usage
        yield prompt_with_history
        yield SimpleNamespace(
            result={
                "content": current_result.content,
                "metadata": current_result.metadata,
                "tool_calls": current_result.tool_calls,
            }
        )
