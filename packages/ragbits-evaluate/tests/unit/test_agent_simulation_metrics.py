"""Tests for agent simulation metrics collectors."""

import time

from ragbits.evaluate.agent_simulation.metrics import (
    CompositeMetricCollector,
    DeepEvalAllMetricsCollector,
    DeepEvalCompletenessMetricCollector,
    DeepEvalKnowledgeRetentionMetricCollector,
    DeepEvalRelevancyMetricCollector,
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

    @staticmethod
    def test_deepeval_completeness_is_metric_collector() -> None:
        """Test DeepEvalCompletenessMetricCollector satisfies MetricCollector protocol."""
        collector = DeepEvalCompletenessMetricCollector()
        assert isinstance(collector, MetricCollector)

    @staticmethod
    def test_deepeval_relevancy_is_metric_collector() -> None:
        """Test DeepEvalRelevancyMetricCollector satisfies MetricCollector protocol."""
        collector = DeepEvalRelevancyMetricCollector()
        assert isinstance(collector, MetricCollector)

    @staticmethod
    def test_deepeval_knowledge_retention_is_metric_collector() -> None:
        """Test DeepEvalKnowledgeRetentionMetricCollector satisfies MetricCollector protocol."""
        collector = DeepEvalKnowledgeRetentionMetricCollector()
        assert isinstance(collector, MetricCollector)

    @staticmethod
    def test_deepeval_all_metrics_is_metric_collector() -> None:
        """Test DeepEvalAllMetricsCollector satisfies MetricCollector protocol."""
        collector = DeepEvalAllMetricsCollector()
        assert isinstance(collector, MetricCollector)


class TestDeepEvalMetricCollectors:
    """Tests for DeepEval metric collectors (without actual DeepEval evaluation)."""

    @staticmethod
    def test_completeness_collector_empty() -> None:
        """Test completeness collector with no turns returns empty dict."""
        collector = DeepEvalCompletenessMetricCollector()
        result = collector.on_conversation_end([])
        assert result == {}

    @staticmethod
    def test_completeness_collector_records_turns() -> None:
        """Test completeness collector records turns correctly."""
        collector = DeepEvalCompletenessMetricCollector()

        turn = _make_turn_result(1)
        collector.on_turn_start(1, 0, "Hello")
        collector.on_turn_end(turn)

        # Should have recorded the turn
        assert len(collector._turns) == 1
        assert collector._turns[0] == ("User message 1", "Assistant response 1")

    @staticmethod
    def test_completeness_collector_reset() -> None:
        """Test completeness collector reset."""
        collector = DeepEvalCompletenessMetricCollector()

        turn = _make_turn_result(1)
        collector.on_turn_end(turn)

        collector.reset()
        assert collector._turns == []

    @staticmethod
    def test_relevancy_collector_empty() -> None:
        """Test relevancy collector with no turns returns empty dict."""
        collector = DeepEvalRelevancyMetricCollector()
        result = collector.on_conversation_end([])
        assert result == {}

    @staticmethod
    def test_relevancy_collector_records_turns() -> None:
        """Test relevancy collector records turns correctly."""
        collector = DeepEvalRelevancyMetricCollector()

        turn = _make_turn_result(1)
        collector.on_turn_end(turn)

        assert len(collector._turns) == 1

    @staticmethod
    def test_knowledge_retention_collector_empty() -> None:
        """Test knowledge retention collector with no turns returns empty dict."""
        collector = DeepEvalKnowledgeRetentionMetricCollector()
        result = collector.on_conversation_end([])
        assert result == {}

    @staticmethod
    def test_all_metrics_collector_delegates() -> None:
        """Test all metrics collector delegates to child collectors."""
        collector = DeepEvalAllMetricsCollector()

        turn = _make_turn_result(1)
        collector.on_turn_start(1, 0, "Hello")
        collector.on_turn_end(turn)

        # Check that child collectors received the turn
        assert len(collector._completeness._turns) == 1
        assert len(collector._relevancy._turns) == 1
        assert len(collector._knowledge_retention._turns) == 1

    @staticmethod
    def test_all_metrics_collector_reset() -> None:
        """Test all metrics collector resets all children."""
        collector = DeepEvalAllMetricsCollector()

        turn = _make_turn_result(1)
        collector.on_turn_end(turn)

        collector.reset()

        assert collector._completeness._turns == []
        assert collector._relevancy._turns == []
        assert collector._knowledge_retention._turns == []


class TestSimulationConfigMetricsValidation:
    """Tests for SimulationConfig metrics field validation."""

    @staticmethod
    def test_metrics_with_classes() -> None:
        """Test that passing classes (types) works correctly."""
        from ragbits.evaluate.agent_simulation.models import SimulationConfig

        config = SimulationConfig(metrics=[LatencyMetricCollector, TokenUsageMetricCollector])
        assert len(config.metrics) == 2
        assert config.metrics[0] is LatencyMetricCollector
        assert config.metrics[1] is TokenUsageMetricCollector

    @staticmethod
    def test_create_metric_collectors_creates_fresh_instances() -> None:
        """Test that create_metric_collectors creates fresh instances each time."""
        from ragbits.evaluate.agent_simulation.models import SimulationConfig

        config = SimulationConfig(metrics=[LatencyMetricCollector, TokenUsageMetricCollector])

        # Create instances twice
        collectors1 = config.create_metric_collectors()
        collectors2 = config.create_metric_collectors()

        # Should be different instances
        assert collectors1[0] is not collectors2[0]
        assert collectors1[1] is not collectors2[1]

        # But same types
        assert isinstance(collectors1[0], LatencyMetricCollector)
        assert isinstance(collectors2[0], LatencyMetricCollector)

    @staticmethod
    def test_metrics_with_lambda_factory() -> None:
        """Test that lambda factories work for collectors with arguments."""
        from ragbits.evaluate.agent_simulation.models import SimulationConfig

        # Use lambda for potential custom collector with args
        config = SimulationConfig(metrics=[lambda: LatencyMetricCollector()])
        collectors = config.create_metric_collectors()

        assert len(collectors) == 1
        assert isinstance(collectors[0], LatencyMetricCollector)

    @staticmethod
    def test_metrics_none_is_valid() -> None:
        """Test that None metrics is valid."""
        from ragbits.evaluate.agent_simulation.models import SimulationConfig

        config = SimulationConfig(metrics=None)
        assert config.metrics is None
        assert config.create_metric_collectors() == []

    @staticmethod
    def test_metrics_empty_list_is_valid() -> None:
        """Test that empty list metrics is valid."""
        from ragbits.evaluate.agent_simulation.models import SimulationConfig

        config = SimulationConfig(metrics=[])
        assert config.metrics == []
        assert config.create_metric_collectors() == []
