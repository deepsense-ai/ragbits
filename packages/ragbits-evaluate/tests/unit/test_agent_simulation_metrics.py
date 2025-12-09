"""Tests for agent simulation metrics collectors."""

import time

from ragbits.evaluate.agent_simulation.metrics import (
    CompositeMetricCollector,
    LatencyMetricCollector,
    MetricCollector,
    TokenUsageMetricCollector,
    ToolUsageMetricCollector,
)
from ragbits.evaluate.agent_simulation.results import TurnResult


def _make_turn_result(
    turn_index: int = 1,
    task_index: int = 0,
    token_usage: dict[str, int] | None = None,
    tool_calls: list[dict] | None = None,
) -> TurnResult:
    """Create a TurnResult for testing."""
    return TurnResult(
        turn_index=turn_index,
        task_index=task_index,
        user_message=f"User message {turn_index}",
        assistant_message=f"Assistant response {turn_index}",
        tool_calls=tool_calls or [],
        task_completed=False,
        task_completed_reason="",
        token_usage=token_usage,
    )


class TestLatencyMetricCollector:
    """Tests for LatencyMetricCollector."""

    @staticmethod
    def test_latency_collector_empty() -> None:
        """Test latency collector with no turns."""
        collector = LatencyMetricCollector()
        result = collector.on_conversation_end([])
        assert result == {}

    @staticmethod
    def test_latency_collector_single_turn() -> None:
        """Test latency collector with single turn."""
        collector = LatencyMetricCollector()

        collector.on_turn_start(1, 0, "Hello")
        time.sleep(0.01)  # Small delay
        turn_result = _make_turn_result(1)
        collector.on_turn_end(turn_result)

        result = collector.on_conversation_end([turn_result])

        assert "latency_avg_ms" in result
        assert "latency_max_ms" in result
        assert "latency_min_ms" in result
        assert "latency_per_turn_ms" in result
        assert result["latency_avg_ms"] >= 10  # At least 10ms
        assert len(result["latency_per_turn_ms"]) == 1

    @staticmethod
    def test_latency_collector_multiple_turns() -> None:
        """Test latency collector with multiple turns."""
        collector = LatencyMetricCollector()
        turns = []

        for i in range(3):
            collector.on_turn_start(i + 1, 0, f"Message {i}")
            time.sleep(0.005)  # 5ms delay
            turn = _make_turn_result(i + 1)
            collector.on_turn_end(turn)
            turns.append(turn)

        result = collector.on_conversation_end(turns)

        assert len(result["latency_per_turn_ms"]) == 3
        assert result["latency_avg_ms"] == sum(result["latency_per_turn_ms"]) / 3
        assert result["latency_max_ms"] == max(result["latency_per_turn_ms"])
        assert result["latency_min_ms"] == min(result["latency_per_turn_ms"])

    @staticmethod
    def test_latency_collector_reset() -> None:
        """Test latency collector reset."""
        collector = LatencyMetricCollector()

        collector.on_turn_start(1, 0, "Hello")
        turn = _make_turn_result(1)
        collector.on_turn_end(turn)

        collector.reset()

        result = collector.on_conversation_end([])
        assert result == {}


class TestTokenUsageMetricCollector:
    """Tests for TokenUsageMetricCollector."""

    @staticmethod
    def test_token_collector_empty() -> None:
        """Test token collector with no turns."""
        collector = TokenUsageMetricCollector()
        result = collector.on_conversation_end([])
        assert result == {}

    @staticmethod
    def test_token_collector_single_turn() -> None:
        """Test token collector with single turn."""
        collector = TokenUsageMetricCollector()

        turn = _make_turn_result(1, token_usage={"total": 100, "prompt": 80, "completion": 20})
        collector.on_turn_start(1, 0, "Hello")
        collector.on_turn_end(turn)

        result = collector.on_conversation_end([turn])

        assert result["tokens_total"] == 100
        assert result["tokens_prompt"] == 80
        assert result["tokens_completion"] == 20
        assert result["tokens_avg_per_turn"] == 100
        assert result["tokens_per_turn"] == [100]

    @staticmethod
    def test_token_collector_multiple_turns() -> None:
        """Test token collector with multiple turns."""
        collector = TokenUsageMetricCollector()
        turns = []

        for i in range(3):
            turn = _make_turn_result(
                i + 1,
                token_usage={"total": (i + 1) * 100, "prompt": (i + 1) * 80, "completion": (i + 1) * 20},
            )
            collector.on_turn_start(i + 1, 0, f"Message {i}")
            collector.on_turn_end(turn)
            turns.append(turn)

        result = collector.on_conversation_end(turns)

        assert result["tokens_total"] == 600  # 100 + 200 + 300
        assert result["tokens_prompt"] == 480  # 80 + 160 + 240
        assert result["tokens_completion"] == 120  # 20 + 40 + 60
        assert result["tokens_avg_per_turn"] == 200
        assert result["tokens_per_turn"] == [100, 200, 300]

    @staticmethod
    def test_token_collector_missing_usage() -> None:
        """Test token collector with missing token usage."""
        collector = TokenUsageMetricCollector()

        turn = _make_turn_result(1, token_usage=None)
        collector.on_turn_end(turn)

        result = collector.on_conversation_end([turn])

        assert result["tokens_total"] == 0
        assert result["tokens_per_turn"] == [0]

    @staticmethod
    def test_token_collector_reset() -> None:
        """Test token collector reset."""
        collector = TokenUsageMetricCollector()

        turn = _make_turn_result(1, token_usage={"total": 100, "prompt": 80, "completion": 20})
        collector.on_turn_end(turn)

        collector.reset()

        result = collector.on_conversation_end([])
        assert result == {}


class TestToolUsageMetricCollector:
    """Tests for ToolUsageMetricCollector."""

    @staticmethod
    def test_tool_collector_empty() -> None:
        """Test tool collector with no turns."""
        collector = ToolUsageMetricCollector()
        result = collector.on_conversation_end([])

        assert result["tools_total_calls"] == 0
        assert result["tools_unique"] == []
        assert result["tools_counts"] == {}
        assert result["tools_per_turn"] == []
        assert result["turns_with_tools"] == 0

    @staticmethod
    def test_tool_collector_single_turn_with_tools() -> None:
        """Test tool collector with single turn containing tool calls."""
        collector = ToolUsageMetricCollector()

        turn = _make_turn_result(
            1,
            tool_calls=[
                {"name": "search", "arguments": {}, "result": "results"},
                {"name": "lookup", "arguments": {}, "result": "data"},
            ],
        )
        collector.on_turn_end(turn)

        result = collector.on_conversation_end([turn])

        assert result["tools_total_calls"] == 2
        assert set(result["tools_unique"]) == {"search", "lookup"}
        assert result["tools_counts"]["search"] == 1
        assert result["tools_counts"]["lookup"] == 1
        assert result["tools_per_turn"] == [["search", "lookup"]]
        assert result["turns_with_tools"] == 1

    @staticmethod
    def test_tool_collector_multiple_turns() -> None:
        """Test tool collector with multiple turns."""
        collector = ToolUsageMetricCollector()
        turns = []

        # Turn 1: search tool
        turn1 = _make_turn_result(1, tool_calls=[{"name": "search", "arguments": {}, "result": "r1"}])
        collector.on_turn_end(turn1)
        turns.append(turn1)

        # Turn 2: no tools
        turn2 = _make_turn_result(2, tool_calls=[])
        collector.on_turn_end(turn2)
        turns.append(turn2)

        # Turn 3: search and calculate
        turn3 = _make_turn_result(
            3,
            tool_calls=[
                {"name": "search", "arguments": {}, "result": "r2"},
                {"name": "calculate", "arguments": {}, "result": "42"},
            ],
        )
        collector.on_turn_end(turn3)
        turns.append(turn3)

        result = collector.on_conversation_end(turns)

        assert result["tools_total_calls"] == 3
        assert set(result["tools_unique"]) == {"search", "calculate"}
        assert result["tools_counts"]["search"] == 2
        assert result["tools_counts"]["calculate"] == 1
        assert result["tools_per_turn"] == [["search"], [], ["search", "calculate"]]
        assert result["turns_with_tools"] == 2

    @staticmethod
    def test_tool_collector_reset() -> None:
        """Test tool collector reset."""
        collector = ToolUsageMetricCollector()

        turn = _make_turn_result(1, tool_calls=[{"name": "search", "arguments": {}, "result": "r"}])
        collector.on_turn_end(turn)

        collector.reset()

        result = collector.on_conversation_end([])
        assert result["tools_total_calls"] == 0
        assert result["tools_unique"] == []


class TestCompositeMetricCollector:
    """Tests for CompositeMetricCollector."""

    @staticmethod
    def test_composite_empty() -> None:
        """Test composite collector with no child collectors."""
        composite = CompositeMetricCollector()
        result = composite.on_conversation_end([])
        assert result == {}

    @staticmethod
    def test_composite_single_collector() -> None:
        """Test composite with single collector."""
        token_collector = TokenUsageMetricCollector()
        composite = CompositeMetricCollector([token_collector])

        turn = _make_turn_result(1, token_usage={"total": 100, "prompt": 80, "completion": 20})
        composite.on_turn_start(1, 0, "Hello")
        composite.on_turn_end(turn)

        result = composite.on_conversation_end([turn])

        assert "tokens_total" in result
        assert result["tokens_total"] == 100

    @staticmethod
    def test_composite_multiple_collectors() -> None:
        """Test composite with multiple collectors."""
        token_collector = TokenUsageMetricCollector()
        tool_collector = ToolUsageMetricCollector()
        composite = CompositeMetricCollector([token_collector, tool_collector])

        turn = _make_turn_result(
            1,
            token_usage={"total": 100, "prompt": 80, "completion": 20},
            tool_calls=[{"name": "search", "arguments": {}, "result": "r"}],
        )
        composite.on_turn_start(1, 0, "Hello")
        composite.on_turn_end(turn)

        result = composite.on_conversation_end([turn])

        # Token metrics
        assert "tokens_total" in result
        assert result["tokens_total"] == 100

        # Tool metrics
        assert "tools_total_calls" in result
        assert result["tools_total_calls"] == 1

    @staticmethod
    def test_composite_add_collector() -> None:
        """Test adding collector to composite."""
        composite = CompositeMetricCollector()
        composite.add(TokenUsageMetricCollector())

        turn = _make_turn_result(1, token_usage={"total": 50, "prompt": 40, "completion": 10})
        composite.on_turn_end(turn)

        result = composite.on_conversation_end([turn])
        assert result["tokens_total"] == 50

    @staticmethod
    def test_composite_reset() -> None:
        """Test composite reset."""
        token_collector = TokenUsageMetricCollector()
        composite = CompositeMetricCollector([token_collector])

        turn = _make_turn_result(1, token_usage={"total": 100, "prompt": 80, "completion": 20})
        composite.on_turn_end(turn)

        composite.reset()

        result = composite.on_conversation_end([])
        assert result == {}


class TestMetricCollectorProtocol:
    """Tests for MetricCollector protocol compliance."""

    @staticmethod
    def test_latency_collector_is_metric_collector() -> None:
        """Test LatencyMetricCollector satisfies MetricCollector protocol."""
        collector = LatencyMetricCollector()
        assert isinstance(collector, MetricCollector)

    @staticmethod
    def test_token_collector_is_metric_collector() -> None:
        """Test TokenUsageMetricCollector satisfies MetricCollector protocol."""
        collector = TokenUsageMetricCollector()
        assert isinstance(collector, MetricCollector)

    @staticmethod
    def test_tool_collector_is_metric_collector() -> None:
        """Test ToolUsageMetricCollector satisfies MetricCollector protocol."""
        collector = ToolUsageMetricCollector()
        assert isinstance(collector, MetricCollector)
