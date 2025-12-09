"""Tests for response adapters."""

from __future__ import annotations

from typing import Any, AsyncGenerator
from unittest.mock import MagicMock

import pytest

from ragbits.chat.adapters import (
    AdapterContext,
    AdapterPipeline,
    BaseAdapter,
    FilterAdapter,
    TextAccumulatorAdapter,
    ToolCallAccumulatorAdapter,
    ToolResultTextAdapter,
    UsageAggregatorAdapter,
)


class TestAdapterContext:
    """Tests for AdapterContext."""

    @staticmethod
    def test_adapter_context_creation() -> None:
        """Test basic AdapterContext creation."""
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        assert context.turn_index == 1
        assert context.task_index == 0
        assert context.user_message == "Hello"
        assert context.history == []
        assert context.text_parts == []
        assert context.tool_calls == []
        assert context.metadata == {}

    @staticmethod
    def test_adapter_context_with_defaults() -> None:
        """Test AdapterContext with custom accumulators."""
        context = AdapterContext(
            turn_index=2,
            task_index=1,
            user_message="Test",
            history=[],
            text_parts=["existing"],
            metadata={"key": "value"},
        )

        assert context.text_parts == ["existing"]
        assert context.metadata == {"key": "value"}


class TestBaseAdapter:
    """Tests for BaseAdapter."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_base_adapter_passthrough() -> None:
        """Test BaseAdapter default passthrough behavior."""
        adapter = BaseAdapter()
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in adapter.adapt("test", context):
            results.append(chunk)

        assert results == ["test"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_base_adapter_on_stream_start() -> None:
        """Test BaseAdapter on_stream_start is a no-op."""
        adapter = BaseAdapter()
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        # Should not raise
        await adapter.on_stream_start(context)

    @staticmethod
    @pytest.mark.asyncio
    async def test_base_adapter_on_stream_end() -> None:
        """Test BaseAdapter on_stream_end emits nothing."""
        adapter = BaseAdapter()
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in adapter.on_stream_end(context):
            results.append(chunk)

        assert results == []

    @staticmethod
    def test_base_adapter_reset() -> None:
        """Test BaseAdapter reset is a no-op."""
        adapter = BaseAdapter()
        adapter.reset()  # Should not raise


class TestFilterAdapter:
    """Tests for FilterAdapter."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_filter_adapter_exclude_types() -> None:
        """Test FilterAdapter excludes specified types."""
        adapter = FilterAdapter(exclude_types=(int, float))
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        # String should pass through
        results = []
        async for chunk in adapter.adapt("hello", context):
            results.append(chunk)
        assert results == ["hello"]

        # Int should be filtered
        results = []
        async for chunk in adapter.adapt(42, context):
            results.append(chunk)
        assert results == []

        # Float should be filtered
        results = []
        async for chunk in adapter.adapt(3.14, context):
            results.append(chunk)
        assert results == []

    @staticmethod
    @pytest.mark.asyncio
    async def test_filter_adapter_include_types() -> None:
        """Test FilterAdapter includes only specified types."""
        adapter = FilterAdapter(include_types=(str,))
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        # String should pass through
        results = []
        async for chunk in adapter.adapt("hello", context):
            results.append(chunk)
        assert results == ["hello"]

        # Int should be filtered
        results = []
        async for chunk in adapter.adapt(42, context):
            results.append(chunk)
        assert results == []

    @staticmethod
    def test_filter_adapter_input_output_types() -> None:
        """Test FilterAdapter declares correct types."""
        adapter = FilterAdapter()
        assert adapter.input_types == (object,)
        assert adapter.output_types == (object,)


class TestTextAccumulatorAdapter:
    """Tests for TextAccumulatorAdapter."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_text_accumulator_stores_and_emits() -> None:
        """Test TextAccumulatorAdapter stores text and emits when configured."""
        adapter = TextAccumulatorAdapter(emit=True)
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in adapter.adapt("chunk1", context):
            results.append(chunk)
        async for chunk in adapter.adapt("chunk2", context):
            results.append(chunk)

        assert results == ["chunk1", "chunk2"]
        assert context.text_parts == ["chunk1", "chunk2"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_text_accumulator_stores_without_emit() -> None:
        """Test TextAccumulatorAdapter stores but doesn't emit when configured."""
        adapter = TextAccumulatorAdapter(emit=False)
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in adapter.adapt("chunk1", context):
            results.append(chunk)

        assert results == []
        assert context.text_parts == ["chunk1"]


class TestToolCallAccumulatorAdapter:
    """Tests for ToolCallAccumulatorAdapter."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_tool_call_accumulator_stores_and_emits() -> None:
        """Test ToolCallAccumulatorAdapter stores tool calls and emits."""
        adapter = ToolCallAccumulatorAdapter(emit=True)
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        # Create mock tool call result
        mock_tool_call = MagicMock()
        mock_tool_call.name = "test_tool"

        results = []
        async for chunk in adapter.adapt(mock_tool_call, context):
            results.append(chunk)

        assert results == [mock_tool_call]
        assert context.tool_calls == [mock_tool_call]


class TestToolResultTextAdapter:
    """Tests for ToolResultTextAdapter."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_tool_result_text_adapter_with_renderer() -> None:
        """Test ToolResultTextAdapter renders tool result as text."""

        async def render_test_tool(tool_call: Any) -> str:
            return f"Rendered: {tool_call.name}"

        adapter = ToolResultTextAdapter(
            renderers={"test_tool": render_test_tool},
            pass_through=True,
        )
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.name = "test_tool"

        results = []
        async for chunk in adapter.adapt(mock_tool_call, context):
            results.append(chunk)

        assert len(results) == 2
        assert results[0] == "Rendered: test_tool"
        assert results[1] == mock_tool_call

    @staticmethod
    @pytest.mark.asyncio
    async def test_tool_result_text_adapter_without_passthrough() -> None:
        """Test ToolResultTextAdapter without pass-through."""

        async def render_test_tool(tool_call: Any) -> str:
            return f"Rendered: {tool_call.name}"

        adapter = ToolResultTextAdapter(
            renderers={"test_tool": render_test_tool},
            pass_through=False,
        )
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.name = "test_tool"

        results = []
        async for chunk in adapter.adapt(mock_tool_call, context):
            results.append(chunk)

        assert len(results) == 1
        assert results[0] == "Rendered: test_tool"

    @staticmethod
    @pytest.mark.asyncio
    async def test_tool_result_text_adapter_no_renderer() -> None:
        """Test ToolResultTextAdapter without matching renderer."""
        adapter = ToolResultTextAdapter(pass_through=True)
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.name = "unknown_tool"

        results = []
        async for chunk in adapter.adapt(mock_tool_call, context):
            results.append(chunk)

        # Only pass-through, no rendered text
        assert len(results) == 1
        assert results[0] == mock_tool_call

    @staticmethod
    @pytest.mark.asyncio
    async def test_tool_result_text_adapter_default_renderer() -> None:
        """Test ToolResultTextAdapter with default renderer."""

        async def default_render(tool_call: Any) -> str:
            return f"Default: {tool_call.name}"

        adapter = ToolResultTextAdapter(
            default_renderer=default_render,
            pass_through=False,
        )
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.name = "any_tool"

        results = []
        async for chunk in adapter.adapt(mock_tool_call, context):
            results.append(chunk)

        assert results == ["Default: any_tool"]


class TestUsageAggregatorAdapter:
    """Tests for UsageAggregatorAdapter."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_usage_aggregator_accumulates() -> None:
        """Test UsageAggregatorAdapter accumulates usage."""
        from ragbits.core.llms import Usage
        from ragbits.core.llms.base import UsageItem

        adapter = UsageAggregatorAdapter(emit_per_chunk=False, emit_aggregated_at_end=True)
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        # Usage works via requests list, not direct token fields
        usage1 = Usage(
            requests=[
                UsageItem(
                    model="test-model",
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    estimated_cost=0.001,
                )
            ]
        )
        usage2 = Usage(
            requests=[
                UsageItem(
                    model="test-model",
                    prompt_tokens=20,
                    completion_tokens=10,
                    total_tokens=30,
                    estimated_cost=0.002,
                )
            ]
        )

        # Process usage chunks (should not emit per chunk)
        results = []
        async for chunk in adapter.adapt(usage1, context):
            results.append(chunk)
        async for chunk in adapter.adapt(usage2, context):
            results.append(chunk)

        assert results == []

        # Get aggregated at end
        end_results = []
        async for chunk in adapter.on_stream_end(context):
            end_results.append(chunk)

        assert len(end_results) == 1
        total = end_results[0]
        assert total.prompt_tokens == 30
        assert total.completion_tokens == 15
        assert total.total_tokens == 45

    @staticmethod
    @pytest.mark.asyncio
    async def test_usage_aggregator_emit_per_chunk() -> None:
        """Test UsageAggregatorAdapter emits per chunk when configured."""
        from ragbits.core.llms import Usage
        from ragbits.core.llms.base import UsageItem

        adapter = UsageAggregatorAdapter(emit_per_chunk=True, emit_aggregated_at_end=False)
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        usage1 = Usage(
            requests=[
                UsageItem(
                    model="test-model",
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    estimated_cost=0.001,
                )
            ]
        )

        results = []
        async for chunk in adapter.adapt(usage1, context):
            results.append(chunk)

        assert results == [usage1]

    @staticmethod
    def test_usage_aggregator_reset() -> None:
        """Test UsageAggregatorAdapter reset clears accumulated usage."""
        from ragbits.core.llms import Usage
        from ragbits.core.llms.base import UsageItem

        adapter = UsageAggregatorAdapter()
        adapter._total = Usage(
            requests=[
                UsageItem(
                    model="test-model",
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    estimated_cost=0.01,
                )
            ]
        )

        adapter.reset()

        assert adapter._total is None
        assert adapter.get_total() is None


class TestAdapterPipeline:
    """Tests for AdapterPipeline."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_pipeline_processes_stream() -> None:
        """Test AdapterPipeline processes stream through adapters."""

        async def input_stream() -> AsyncGenerator[str, None]:
            yield "hello"
            yield "world"

        pipeline = AdapterPipeline([TextAccumulatorAdapter(emit=True)])
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in pipeline.process(input_stream(), context):
            results.append(chunk)

        assert results == ["hello", "world"]
        assert context.text_parts == ["hello", "world"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_pipeline_chains_adapters() -> None:
        """Test AdapterPipeline chains multiple adapters."""

        class UppercaseAdapter(BaseAdapter):
            @property
            def input_types(self) -> tuple[type, ...]:
                return (str,)

            @property
            def output_types(self) -> tuple[type, ...]:
                return (str,)

            async def adapt(
                self,
                chunk: str,
                context: AdapterContext,
            ) -> AsyncGenerator[str, None]:
                yield chunk.upper()

        async def input_stream() -> AsyncGenerator[str | int, None]:
            yield "hello"
            yield 42  # Should pass through unchanged
            yield "world"

        pipeline = AdapterPipeline([
            UppercaseAdapter(),
            FilterAdapter(exclude_types=(int,)),
        ])
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in pipeline.process(input_stream(), context):
            results.append(chunk)

        assert results == ["HELLO", "WORLD"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_pipeline_calls_lifecycle_hooks() -> None:
        """Test AdapterPipeline calls lifecycle hooks."""
        start_called = []
        end_called = []

        class TrackingAdapter(BaseAdapter):
            async def on_stream_start(self, context: AdapterContext) -> None:
                start_called.append(True)

            async def on_stream_end(self, context: AdapterContext) -> AsyncGenerator[str, None]:
                end_called.append(True)
                yield "final"

        async def input_stream() -> AsyncGenerator[str, None]:
            yield "test"

        pipeline = AdapterPipeline([TrackingAdapter()])
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in pipeline.process(input_stream(), context):
            results.append(chunk)

        assert start_called == [True]
        assert end_called == [True]
        assert results == ["test", "final"]

    @staticmethod
    def test_pipeline_add_adapter() -> None:
        """Test AdapterPipeline add method."""
        pipeline = AdapterPipeline()
        adapter = FilterAdapter()

        pipeline.add(adapter)

        assert len(pipeline._adapters) == 1
        assert pipeline._adapters[0] is adapter

    @staticmethod
    def test_pipeline_reset() -> None:
        """Test AdapterPipeline reset calls reset on all adapters."""
        from ragbits.core.llms import Usage

        adapter1 = UsageAggregatorAdapter()
        adapter1._total = Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        adapter2 = UsageAggregatorAdapter()
        adapter2._total = Usage(prompt_tokens=200, completion_tokens=100, total_tokens=300)

        pipeline = AdapterPipeline([adapter1, adapter2])
        pipeline.reset()

        assert adapter1._total is None
        assert adapter2._total is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_pipeline_passthrough_non_matching_types() -> None:
        """Test AdapterPipeline passes through non-matching types."""

        class StringOnlyAdapter(BaseAdapter):
            @property
            def input_types(self) -> tuple[type, ...]:
                return (str,)

            @property
            def output_types(self) -> tuple[type, ...]:
                return (str,)

            async def adapt(
                self,
                chunk: str,
                context: AdapterContext,
            ) -> AsyncGenerator[str, None]:
                yield f"[{chunk}]"

        async def input_stream() -> AsyncGenerator[str | int, None]:
            yield "hello"
            yield 42
            yield "world"

        pipeline = AdapterPipeline([StringOnlyAdapter()])
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in pipeline.process(input_stream(), context):
            results.append(chunk)

        # Strings transformed, int passed through
        assert results == ["[hello]", 42, "[world]"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_pipeline_expands_chunks() -> None:
        """Test AdapterPipeline handles adapters that expand 1 to N."""

        class ExpandAdapter(BaseAdapter):
            @property
            def input_types(self) -> tuple[type, ...]:
                return (str,)

            @property
            def output_types(self) -> tuple[type, ...]:
                return (str,)

            async def adapt(
                self,
                chunk: str,
                context: AdapterContext,
            ) -> AsyncGenerator[str, None]:
                for char in chunk:
                    yield char

        async def input_stream() -> AsyncGenerator[str, None]:
            yield "ab"

        pipeline = AdapterPipeline([ExpandAdapter()])
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in pipeline.process(input_stream(), context):
            results.append(chunk)

        assert results == ["a", "b"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_pipeline_filters_chunks() -> None:
        """Test AdapterPipeline handles adapters that filter (1 to 0)."""

        class FilterEmptyAdapter(BaseAdapter):
            @property
            def input_types(self) -> tuple[type, ...]:
                return (str,)

            @property
            def output_types(self) -> tuple[type, ...]:
                return (str,)

            async def adapt(
                self,
                chunk: str,
                context: AdapterContext,
            ) -> AsyncGenerator[str, None]:
                if chunk.strip():
                    yield chunk

        async def input_stream() -> AsyncGenerator[str, None]:
            yield "hello"
            yield ""
            yield "   "
            yield "world"

        pipeline = AdapterPipeline([FilterEmptyAdapter()])
        context = AdapterContext(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            history=[],
        )

        results = []
        async for chunk in pipeline.process(input_stream(), context):
            results.append(chunk)

        assert results == ["hello", "world"]
