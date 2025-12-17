"""Response adapters for transforming chat response streams.

This module provides a composable adapter system for transforming chat responses
through a pipeline of adapters, each handling a specific concern.

Example:
    >>> from ragbits.chat.adapters import (
    ...     AdapterPipeline,
    ...     ChatResponseAdapter,
    ...     FilterAdapter,
    ...     ToolResultTextAdapter,
    ... )
    >>>
    >>> async def render_products(tool_call):
    ...     return f"Found {len(tool_call.result)} products"
    >>>
    >>> pipeline = AdapterPipeline(
    ...     [
    ...         ChatResponseAdapter(),
    ...         FilterAdapter(exclude_types=(SomeUICommand,)),
    ...         ToolResultTextAdapter(
    ...             renderers={"show_products": render_products},
    ...             pass_through=True,
    ...         ),
    ...     ]
    ... )
    >>>
    >>> async for chunk in pipeline.process(chat_stream, context):
    ...     print(chunk)
"""

from ragbits.chat.adapters.builtin import (
    ChatResponseAdapter,
    FilterAdapter,
    TextAccumulatorAdapter,
    ToolCallAccumulatorAdapter,
    ToolResultTextAdapter,
    UsageAggregatorAdapter,
)
from ragbits.chat.adapters.pipeline import AdapterPipeline
from ragbits.chat.adapters.protocol import (
    AdapterContext,
    BaseAdapter,
    ResponseAdapter,
)

__all__ = [
    "AdapterContext",
    "AdapterPipeline",
    "BaseAdapter",
    "ChatResponseAdapter",
    "FilterAdapter",
    "ResponseAdapter",
    "TextAccumulatorAdapter",
    "ToolCallAccumulatorAdapter",
    "ToolResultTextAdapter",
    "UsageAggregatorAdapter",
]
