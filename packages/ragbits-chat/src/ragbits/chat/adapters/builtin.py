"""Built-in adapters for common response transformations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, AsyncGenerator

from ragbits.chat.adapters.protocol import AdapterContext, BaseAdapter

if TYPE_CHECKING:
    from ragbits.agents.tool import ToolCallResult
    from ragbits.chat.interface.types import ChatResponse
    from ragbits.core.llms import Usage


class ChatResponseAdapter(BaseAdapter):
    """Extracts text and content from ChatResponse objects.

    This adapter handles the common case of extracting text from
    ChatResponse objects yielded by production ChatInterface implementations.

    Example:
        >>> adapter = ChatResponseAdapter()
        >>> pipeline = AdapterPipeline([adapter])
        >>> # Processes TextResponse, extracts text, passes through other types
    """

    @property
    def input_types(self) -> tuple[type, ...]:
        # Import at runtime to avoid hard dependency
        from ragbits.chat.interface.types import ChatResponse

        return (ChatResponse,)

    @property
    def output_types(self) -> tuple[type, ...]:
        return (str, object)

    async def adapt(
        self,
        chunk: ChatResponse,
        context: AdapterContext,
    ) -> AsyncGenerator[str | Any, None]:
        """Extract text and embedded content from ChatResponse.

        Args:
            chunk: ChatResponse to process.
            context: Adapter context.

        Yields:
            Extracted text strings and embedded objects.
        """
        # Import types for isinstance checks
        from ragbits.chat.interface.types import TextContent

        content = chunk.content

        # Handle TextContent - extract the text
        if isinstance(content, TextContent):
            if content.text:
                yield content.text
        # Handle other content types - yield the content itself
        elif content is not None:
            yield content


class ToolResultTextAdapter(BaseAdapter):
    """Renders tool call results as human-readable text.

    Use this adapter to make tool results visible in the conversation
    by rendering them as text. Supports per-tool custom renderers.

    Example:
        >>> async def render_products(tool_call):
        ...     return f"Found {len(tool_call.result)} products"
        ...
        >>> adapter = ToolResultTextAdapter(
        ...     renderers={"show_products": render_products},
        ...     pass_through=True,
        ... )
    """

    def __init__(
        self,
        renderers: dict[str, Callable[[ToolCallResult], Awaitable[str]]] | None = None,
        default_renderer: Callable[[ToolCallResult], Awaitable[str]] | None = None,
        pass_through: bool = True,
    ) -> None:
        """Initialize the adapter.

        Args:
            renderers: Tool name to async render function mapping.
            default_renderer: Fallback renderer for tools without specific renderer.
            pass_through: If True, also yield original ToolCallResult after text.
        """
        self._renderers = renderers or {}
        self._default_renderer = default_renderer
        self._pass_through = pass_through

    @property
    def input_types(self) -> tuple[type, ...]:
        from ragbits.agents.tool import ToolCallResult

        return (ToolCallResult,)

    @property
    def output_types(self) -> tuple[type, ...]:
        from ragbits.agents.tool import ToolCallResult

        return (str, ToolCallResult)

    async def adapt(
        self,
        chunk: ToolCallResult,
        context: AdapterContext,
    ) -> AsyncGenerator[str | ToolCallResult, None]:
        """Render tool result as text and optionally pass through.

        Args:
            chunk: ToolCallResult to process.
            context: Adapter context.

        Yields:
            Rendered text and/or original ToolCallResult.
        """
        renderer = self._renderers.get(chunk.name, self._default_renderer)

        if renderer:
            text = await renderer(chunk)
            if text:
                yield text

        if self._pass_through:
            yield chunk


class FilterAdapter(BaseAdapter):
    """Filters out chunks of specified types.

    Use this adapter to remove unwanted types from the stream,
    such as UI-specific commands that aren't needed for evaluation.

    Example:
        >>> adapter = FilterAdapter(
        ...     exclude_types=(ShowSlidersCommand, ShowOrderCommand),
        ... )
        >>> # These command types will be filtered out
    """

    def __init__(
        self,
        exclude_types: tuple[type, ...] = (),
        include_types: tuple[type, ...] | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            exclude_types: Types to filter out (blacklist).
            include_types: If set, only these types pass through (whitelist).
                          Takes precedence over exclude_types.
        """
        self._exclude = exclude_types
        self._include = include_types

    @property
    def input_types(self) -> tuple[type, ...]:
        return (object,)

    @property
    def output_types(self) -> tuple[type, ...]:
        return (object,)

    async def adapt(
        self,
        chunk: Any,
        context: AdapterContext,
    ) -> AsyncGenerator[Any, None]:
        """Filter chunks based on type.

        Args:
            chunk: Any chunk to potentially filter.
            context: Adapter context.

        Yields:
            The chunk if it passes the filter, nothing otherwise.
        """
        if self._include is not None:
            if isinstance(chunk, self._include):
                yield chunk
        elif not isinstance(chunk, self._exclude):
            yield chunk


class TextAccumulatorAdapter(BaseAdapter):
    """Accumulates text chunks into context for other adapters.

    This adapter stores text in `context.text_parts` and optionally
    passes through the original text chunks.

    Example:
        >>> adapter = TextAccumulatorAdapter(emit=True)
        >>> # Text chunks are stored in context.text_parts and passed through
    """

    def __init__(self, emit: bool = True) -> None:
        """Initialize the adapter.

        Args:
            emit: If True, also yield text chunks (pass-through).
        """
        self._emit = emit

    @property
    def input_types(self) -> tuple[type, ...]:
        return (str,)

    @property
    def output_types(self) -> tuple[type, ...]:
        return (str,) if self._emit else ()

    async def adapt(
        self,
        chunk: str,
        context: AdapterContext,
    ) -> AsyncGenerator[str, None]:
        """Accumulate text and optionally emit.

        Args:
            chunk: Text string to accumulate.
            context: Adapter context.

        Yields:
            The text chunk if emit is True.
        """
        context.text_parts.append(chunk)
        if self._emit:
            yield chunk


class ToolCallAccumulatorAdapter(BaseAdapter):
    """Accumulates tool calls into context for other adapters.

    This adapter stores ToolCallResult in `context.tool_calls` and
    optionally passes through the original chunks.

    Example:
        >>> adapter = ToolCallAccumulatorAdapter(emit=True)
        >>> # Tool calls are stored in context.tool_calls and passed through
    """

    def __init__(self, emit: bool = True) -> None:
        """Initialize the adapter.

        Args:
            emit: If True, also yield tool call chunks (pass-through).
        """
        self._emit = emit

    @property
    def input_types(self) -> tuple[type, ...]:
        from ragbits.agents.tool import ToolCallResult

        return (ToolCallResult,)

    @property
    def output_types(self) -> tuple[type, ...]:
        from ragbits.agents.tool import ToolCallResult

        return (ToolCallResult,) if self._emit else ()

    async def adapt(
        self,
        chunk: ToolCallResult,
        context: AdapterContext,
    ) -> AsyncGenerator[ToolCallResult, None]:
        """Accumulate tool call and optionally emit.

        Args:
            chunk: ToolCallResult to accumulate.
            context: Adapter context.

        Yields:
            The tool call if emit is True.
        """
        context.tool_calls.append(chunk)
        if self._emit:
            yield chunk


class UsageAggregatorAdapter(BaseAdapter):
    """Aggregates token usage across chunks.

    This adapter accumulates Usage objects and can emit per-chunk
    and/or aggregated usage at stream end.

    Example:
        >>> adapter = UsageAggregatorAdapter(
        ...     emit_per_chunk=False,
        ...     emit_aggregated_at_end=True,
        ... )
        >>> # Single aggregated Usage emitted at end
    """

    def __init__(
        self,
        emit_per_chunk: bool = False,
        emit_aggregated_at_end: bool = True,
    ) -> None:
        """Initialize the adapter.

        Args:
            emit_per_chunk: If True, yield each Usage chunk as received.
            emit_aggregated_at_end: If True, yield aggregated Usage at stream end.
        """
        self._emit_per_chunk = emit_per_chunk
        self._emit_at_end = emit_aggregated_at_end
        self._total: Usage | None = None

    @property
    def input_types(self) -> tuple[type, ...]:
        from ragbits.core.llms import Usage

        return (Usage,)

    @property
    def output_types(self) -> tuple[type, ...]:
        from ragbits.core.llms import Usage

        return (Usage,)

    async def adapt(
        self,
        chunk: Usage,
        context: AdapterContext,
    ) -> AsyncGenerator[Usage, None]:
        """Aggregate usage and optionally emit per-chunk.

        Args:
            chunk: Usage to aggregate.
            context: Adapter context.

        Yields:
            The Usage chunk if emit_per_chunk is True.
        """
        if self._total is None:
            self._total = chunk
        else:
            self._total = self._total + chunk

        if self._emit_per_chunk:
            yield chunk

    async def on_stream_end(self, context: AdapterContext) -> AsyncGenerator[Usage, None]:
        """Emit aggregated usage at stream end.

        Args:
            context: Adapter context.

        Yields:
            Aggregated Usage if emit_aggregated_at_end is True and we have data.
        """
        if self._emit_at_end and self._total is not None:
            yield self._total

    def get_total(self) -> Usage | None:
        """Get the accumulated total usage.

        Returns:
            The aggregated Usage or None if no usage was recorded.
        """
        return self._total

    def reset(self) -> None:
        """Reset accumulated usage for reuse."""
        self._total = None
