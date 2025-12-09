"""Protocol and context definitions for response adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Protocol, runtime_checkable


@dataclass
class AdapterContext:
    """Shared context available to all adapters in a pipeline.

    Provides turn-level information and accumulator storage for adapters
    to coordinate and share state during response processing.

    Attributes:
        turn_index: 1-based index of the current turn.
        task_index: 0-based index of the current task.
        user_message: The user message for this turn.
        history: Conversation history before this turn (list of turn objects).
        text_parts: Accumulator for text chunks in the current turn.
        tool_calls: Accumulator for tool calls in the current turn.
        metadata: Extensible metadata storage for custom adapters.
    """

    turn_index: int
    task_index: int
    user_message: str
    history: list[Any]

    # Accumulators for the current turn
    text_parts: list[str] = field(default_factory=list)
    tool_calls: list[Any] = field(default_factory=list)

    # Extensible metadata for custom adapters
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ResponseAdapter(Protocol):
    """Protocol for transforming chat response chunks.

    Implement this protocol to create custom adapters that transform
    chat response streams. Adapters can:
    - Transform chunks (1 -> 1)
    - Expand chunks (1 -> N)
    - Filter chunks (1 -> 0)
    - Pass through non-matching types unchanged

    Example:
        >>> class MyAdapter:
        ...     @property
        ...     def input_types(self) -> tuple[type, ...]:
        ...         return (MyInputType,)
        ...
        ...     @property
        ...     def output_types(self) -> tuple[type, ...]:
        ...         return (str,)
        ...
        ...     async def adapt(
        ...         self,
        ...         chunk: MyInputType,
        ...         context: AdapterContext,
        ...     ) -> AsyncGenerator[str, None]:
        ...         yield f"Transformed: {chunk.value}"
        ...
        ...     async def on_stream_start(self, context: AdapterContext) -> None:
        ...         pass
        ...
        ...     async def on_stream_end(self, context: AdapterContext) -> AsyncGenerator[Any, None]:
        ...         return
        ...         yield  # Make it a generator
        ...
        ...     def reset(self) -> None:
        ...         pass
    """

    @property
    def input_types(self) -> tuple[type, ...]:
        """Types this adapter can process. Others pass through unchanged."""
        ...

    @property
    def output_types(self) -> tuple[type, ...]:
        """Types this adapter may produce."""
        ...

    async def adapt(
        self,
        chunk: Any,
        context: AdapterContext,
    ) -> AsyncGenerator[Any, None]:
        """Transform a single chunk, potentially yielding zero or more output chunks.

        Args:
            chunk: Input chunk to transform.
            context: Shared context for the current turn.

        Yields:
            Transformed chunk(s).
        """
        ...

    async def on_stream_start(self, context: AdapterContext) -> None:
        """Called when a new response stream begins.

        Use for initialization or setup before processing chunks.

        Args:
            context: Shared context for the current turn.
        """
        ...

    async def on_stream_end(self, context: AdapterContext) -> AsyncGenerator[Any, None]:
        """Called when the response stream ends.

        Use for cleanup or emitting final aggregated values.

        Args:
            context: Shared context for the current turn.

        Yields:
            Any final chunks to emit after stream processing.
        """
        ...

    def reset(self) -> None:
        """Reset adapter state for reuse across multiple conversations."""
        ...


class BaseAdapter:
    """Base class providing default implementations for ResponseAdapter.

    Inherit from this class to get sensible defaults and only override
    the methods you need.

    Example:
        >>> class MyAdapter(BaseAdapter):
        ...     @property
        ...     def input_types(self) -> tuple[type, ...]:
        ...         return (str,)
        ...
        ...     @property
        ...     def output_types(self) -> tuple[type, ...]:
        ...         return (str,)
        ...
        ...     async def adapt(
        ...         self,
        ...         chunk: str,
        ...         context: AdapterContext,
        ...     ) -> AsyncGenerator[str, None]:
        ...         yield chunk.upper()
    """

    @property
    def input_types(self) -> tuple[type, ...]:
        """Types this adapter can process."""
        return (object,)

    @property
    def output_types(self) -> tuple[type, ...]:
        """Types this adapter may produce."""
        return (object,)

    async def adapt(
        self,
        chunk: Any,
        context: AdapterContext,
    ) -> AsyncGenerator[Any, None]:
        """Default: pass through unchanged."""
        yield chunk

    async def on_stream_start(self, context: AdapterContext) -> None:
        """Default: no-op."""
        pass

    async def on_stream_end(self, context: AdapterContext) -> AsyncGenerator[Any, None]:
        """Default: emit nothing."""
        return
        yield  # Make it a generator

    def reset(self) -> None:
        """Default: no-op."""
        pass
