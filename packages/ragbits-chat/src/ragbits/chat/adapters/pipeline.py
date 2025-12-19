"""Adapter pipeline for composing multiple response adapters."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from ragbits.chat.adapters.protocol import AdapterContext, ResponseAdapter


class AdapterPipeline:
    """Composes multiple adapters into a single transformation pipeline.

    Chunks flow through adapters in order. Each adapter may:
    - Transform a chunk (1 -> 1)
    - Expand a chunk (1 -> N)
    - Filter a chunk (1 -> 0)
    - Pass through unchanged (for non-matching types)

    Example:
        >>> from ragbits.chat.adapters import (
        ...     AdapterPipeline,
        ...     ChatResponseAdapter,
        ...     FilterAdapter,
        ... )
        >>> pipeline = AdapterPipeline(
        ...     [
        ...         ChatResponseAdapter(),
        ...         FilterAdapter(exclude_types=(SomeCommand,)),
        ...     ]
        ... )
        >>> async for chunk in pipeline.process(stream, context):
        ...     print(chunk)
    """

    def __init__(self, adapters: list[ResponseAdapter] | None = None) -> None:
        """Initialize the pipeline with a list of adapters.

        Args:
            adapters: List of adapters to compose. Order matters - chunks
                     flow through adapters in the order provided.
        """
        self._adapters: list[ResponseAdapter] = adapters or []

    def add(self, adapter: ResponseAdapter) -> None:
        """Add an adapter to the end of the pipeline.

        Args:
            adapter: Adapter to add.
        """
        self._adapters.append(adapter)

    async def process(
        self,
        stream: AsyncGenerator[Any, None],
        context: AdapterContext,
    ) -> AsyncGenerator[Any, None]:
        """Process a stream through all adapters.

        Args:
            stream: Input async generator of chunks.
            context: Shared context for the current turn.

        Yields:
            Transformed chunks after passing through all adapters.
        """
        # Notify adapters of stream start
        for adapter in self._adapters:
            await adapter.on_stream_start(context)

        # Process chunks through pipeline
        async for chunk in stream:
            results: list[Any] = [chunk]

            for adapter in self._adapters:
                next_results: list[Any] = []
                for item in results:
                    if isinstance(item, adapter.input_types):
                        async for transformed in adapter.adapt(item, context):
                            next_results.append(transformed)
                    else:
                        # Pass through unchanged
                        next_results.append(item)
                results = next_results

            for result in results:
                yield result

        # Notify adapters of stream end and collect final emissions
        for adapter in self._adapters:
            async for final_chunk in adapter.on_stream_end(context):
                yield final_chunk

    def reset(self) -> None:
        """Reset all adapters for reuse."""
        for adapter in self._adapters:
            adapter.reset()
