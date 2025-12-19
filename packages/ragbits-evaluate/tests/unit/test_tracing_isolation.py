"""Tests for tracing isolation when running multiple simulations concurrently."""

import asyncio

import pytest

from ragbits.core.audit.traces import clear_trace_handlers, set_trace_handlers, traceable
from ragbits.evaluate.agent_simulation.tracing import MemoryTraceHandler, collect_traces


class TestTracingIsolation:
    """Tests verifying that tracing doesn't interfere between concurrent operations."""

    @staticmethod
    async def test_collect_traces_isolation_sequential() -> None:
        """Test that sequential collect_traces calls don't interfere with each other."""

        @traceable
        def traced_function_a() -> str:
            return "result_a"

        @traceable
        def traced_function_b() -> str:
            return "result_b"

        # First collection
        with collect_traces() as handler1:
            traced_function_a()
            traces1 = handler1.get_traces()

        # Second collection - should not contain traces from first
        with collect_traces() as handler2:
            traced_function_b()
            traces2 = handler2.get_traces()

        # Verify isolation
        assert len(traces1) == 1
        assert "traced_function_a" in traces1[0]["name"]

        assert len(traces2) == 1
        assert "traced_function_b" in traces2[0]["name"]

    @staticmethod
    @pytest.mark.xfail(
        reason="Global trace handlers cause trace leakage between concurrent operations. "
        "Fix requires context-var based handler isolation.",
        strict=True,
    )
    async def test_collect_traces_isolation_concurrent() -> None:
        """Test that concurrent collect_traces calls properly isolate traces.

        This test exposes the issue with global trace handlers - when multiple
        collect_traces contexts are active concurrently, they may interfere
        with each other because they share the global _trace_handlers list.

        Expected behavior (currently failing):
        - Each concurrent simulation should only capture its own traces
        - Traces should not leak between concurrent contexts

        Current behavior (bug):
        - All handlers in the global list receive all traces
        - Concurrent simulations see each other's traces
        """

        @traceable
        async def slow_traced_operation(identifier: str, delay: float) -> str:
            await asyncio.sleep(delay)
            return f"result_{identifier}"

        results: dict[str, list[dict]] = {}
        handler_ids: dict[str, int] = {}

        async def run_simulation(sim_id: str, delay: float) -> None:
            with collect_traces() as handler:
                handler_ids[sim_id] = id(handler)
                await slow_traced_operation(sim_id, delay)
                results[sim_id] = handler.get_traces()

        # Run two simulations concurrently
        await asyncio.gather(
            run_simulation("sim1", 0.1),
            run_simulation("sim2", 0.05),
        )

        # Each handler should be a different object
        assert handler_ids["sim1"] != handler_ids["sim2"], "Handlers should be distinct objects"

        # Check that each simulation got its own traces
        sim1_traces = results["sim1"]
        sim2_traces = results["sim2"]

        # Verify the traces contain the expected operations
        sim1_names = [t["name"] for t in sim1_traces]
        sim2_names = [t["name"] for t in sim2_traces]

        assert any("slow_traced_operation" in n for n in sim1_names), f"sim1 should have its trace, got: {sim1_names}"
        assert any("slow_traced_operation" in n for n in sim2_names), f"sim2 should have its trace, got: {sim2_names}"

        # Verify isolation - each simulation should only see its own trace
        # This is the key assertion that will fail with global handlers
        assert (
            len(sim1_traces) == 1
        ), f"sim1 should have exactly 1 trace (its own), got {len(sim1_traces)}: {sim1_names}"
        assert (
            len(sim2_traces) == 1
        ), f"sim2 should have exactly 1 trace (its own), got {len(sim2_traces)}: {sim2_names}"

    @staticmethod
    async def test_collect_traces_cleanup_on_exception() -> None:
        """Test that trace handlers are properly cleaned up even when exceptions occur."""

        @traceable
        def traced_function() -> str:
            return "result"

        # Cause an exception inside collect_traces
        with pytest.raises(ValueError, match="test error"), collect_traces():  # noqa: PT012
            traced_function()
            raise ValueError("test error")

        # After exception, handlers should be cleared
        # A new collect_traces should work normally
        with collect_traces() as handler:
            traced_function()
            traces = handler.get_traces()

        assert len(traces) == 1
        assert "traced_function" in traces[0]["name"]

    @staticmethod
    async def test_memory_trace_handler_independence() -> None:
        """Test that separate MemoryTraceHandler instances don't share state."""
        handler1 = MemoryTraceHandler()
        handler2 = MemoryTraceHandler()

        # Add spans to handler1
        span1 = handler1.start("operation1", {"input": "data1"})
        handler1.stop({"output": "result1"}, span1)

        # Add spans to handler2
        span2 = handler2.start("operation2", {"input": "data2"})
        handler2.stop({"output": "result2"}, span2)

        # Verify each handler only has its own spans
        traces1 = handler1.get_traces()
        traces2 = handler2.get_traces()

        assert len(traces1) == 1
        assert traces1[0]["name"] == "operation1"

        assert len(traces2) == 1
        assert traces2[0]["name"] == "operation2"

    @staticmethod
    async def test_nested_collect_traces() -> None:
        """Test that nested collect_traces contexts accumulate handlers."""

        @traceable
        def outer_operation() -> str:
            return "outer"

        @traceable
        def inner_operation() -> str:
            return "inner"

        with collect_traces() as outer_handler:
            outer_operation()

            with collect_traces() as inner_handler:
                inner_operation()
                inner_traces = inner_handler.get_traces()

            outer_traces = outer_handler.get_traces()

        # Inner handler should only see inner operation
        assert len(inner_traces) == 1
        assert "inner_operation" in inner_traces[0]["name"]

        # Outer handler should see both (due to how global handlers work)
        # This documents current behavior - outer sees both operations
        outer_names = [t["name"] for t in outer_traces]
        assert any("outer_operation" in n for n in outer_names)

    @staticmethod
    @pytest.mark.xfail(
        reason="Global trace handlers cause trace leakage between concurrent operations. "
        "Fix requires context-var based handler isolation.",
        strict=True,
    )
    async def test_high_concurrency_trace_isolation() -> None:
        """Test trace isolation under high concurrency.

        This test runs 10 concurrent tasks, each with its own trace collection context.
        With proper isolation, each task should only see its own trace.

        Currently fails due to global handler list accumulation.
        """

        @traceable
        async def quick_operation(task_id: int) -> int:
            await asyncio.sleep(0.01)  # Small delay to encourage interleaving
            return task_id

        results: dict[int, list[dict]] = {}

        async def run_task(task_id: int) -> None:
            with collect_traces() as handler:
                await quick_operation(task_id)
                results[task_id] = handler.get_traces()

        # Run 10 concurrent tasks
        await asyncio.gather(*[run_task(i) for i in range(10)])

        # Each task should have captured exactly its own trace
        for task_id, traces in results.items():
            # With proper isolation, each should have 1 trace
            # Document if we see more (indicating leakage)
            if len(traces) != 1:
                pytest.fail(
                    f"Task {task_id} captured {len(traces)} traces instead of 1. "
                    f"This indicates trace leakage between concurrent operations. "
                    f"Trace names: {[t['name'] for t in traces]}"
                )

    @staticmethod
    async def test_global_handler_state_after_concurrent_operations() -> None:
        """Test that global handler state is clean after concurrent operations."""

        @traceable
        async def traced_op() -> str:
            return "done"

        async def run_with_traces() -> None:
            with collect_traces():
                await traced_op()

        # Run concurrent operations
        await asyncio.gather(*[run_with_traces() for _ in range(5)])

        # After all contexts are closed, a new collection should start fresh
        with collect_traces() as handler:
            await traced_op()
            traces = handler.get_traces()

        # Should have exactly 1 trace from our final operation
        assert len(traces) == 1, f"Expected 1 trace after cleanup, got {len(traces)}"


class TestTraceHandlerManagement:
    """Tests for trace handler setup and cleanup."""

    @staticmethod
    def test_set_and_clear_trace_handlers() -> None:
        """Test basic set and clear operations for trace handlers."""
        handler = MemoryTraceHandler()

        # Set handler
        set_trace_handlers(handler)

        # Clear handlers
        clear_trace_handlers()

        # After clearing, collect_traces should create a new handler
        with collect_traces() as new_handler:
            assert new_handler is not handler

    @staticmethod
    def test_multiple_handlers_accumulate() -> None:
        """Test that calling set_trace_handlers multiple times accumulates handlers."""
        clear_trace_handlers()

        handler1 = MemoryTraceHandler()
        handler2 = MemoryTraceHandler()

        set_trace_handlers(handler1)
        set_trace_handlers(handler2)

        # Both handlers should receive traces
        @traceable
        def traced_func() -> str:
            return "result"

        traced_func()

        # Both handlers should have the trace
        assert len(handler1.get_traces()) == 1
        assert len(handler2.get_traces()) == 1

        clear_trace_handlers()
