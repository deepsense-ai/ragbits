"""Tests for agent simulation result models."""

from datetime import datetime, timezone

import pytest

from ragbits.evaluate.agent_simulation.results import (
    ConversationMetrics,
    SimulationResult,
    SimulationStatus,
    TaskResult,
    TurnResult,
)


class TestTurnResult:
    """Tests for TurnResult dataclass."""

    @staticmethod
    def test_turn_result_creation() -> None:
        """Test creating a TurnResult with all fields."""
        turn = TurnResult(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            assistant_message="Hi there!",
            tool_calls=[{"name": "search", "arguments": {"query": "test"}, "result": "found"}],
            task_completed=True,
            task_completed_reason="Task done",
            token_usage={"total": 100, "prompt": 80, "completion": 20},
            latency_ms=150.5,
        )

        assert turn.turn_index == 1
        assert turn.task_index == 0
        assert turn.user_message == "Hello"
        assert turn.assistant_message == "Hi there!"
        assert len(turn.tool_calls) == 1
        assert turn.tool_calls[0]["name"] == "search"
        assert turn.task_completed is True
        assert turn.task_completed_reason == "Task done"
        assert turn.token_usage is not None
        assert turn.token_usage["total"] == 100
        assert turn.latency_ms == 150.5

    @staticmethod
    def test_turn_result_defaults() -> None:
        """Test TurnResult with default values."""
        turn = TurnResult(
            turn_index=1,
            task_index=0,
            user_message="Hello",
            assistant_message="Hi",
        )

        assert turn.tool_calls == []
        assert turn.task_completed is False
        assert turn.task_completed_reason == ""
        assert turn.token_usage is None
        assert turn.latency_ms is None


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    @staticmethod
    def test_task_result_creation() -> None:
        """Test creating a TaskResult."""
        task = TaskResult(
            task_index=0,
            description="Find hotels",
            expected_result="List of hotels",
            completed=True,
            turns_taken=3,
            final_reason="Hotels found",
        )

        assert task.task_index == 0
        assert task.description == "Find hotels"
        assert task.expected_result == "List of hotels"
        assert task.completed is True
        assert task.turns_taken == 3
        assert task.final_reason == "Hotels found"

    @staticmethod
    def test_task_result_with_none_expected() -> None:
        """Test TaskResult with None expected_result."""
        task = TaskResult(
            task_index=0,
            description="Find hotels",
            expected_result=None,
            completed=False,
            turns_taken=1,
            final_reason="Not completed",
        )

        assert task.expected_result is None


class TestConversationMetrics:
    """Tests for ConversationMetrics dataclass."""

    @staticmethod
    def test_conversation_metrics_creation() -> None:
        """Test creating ConversationMetrics with all fields."""
        metrics = ConversationMetrics(
            total_turns=10,
            total_tasks=3,
            tasks_completed=2,
            total_tokens=1500,
            prompt_tokens=1200,
            completion_tokens=300,
            total_cost_usd=0.015,
            deepeval_scores={"completeness": 0.85, "relevancy": 0.90},
            custom={"latency_avg": 200.0},
        )

        assert metrics.total_turns == 10
        assert metrics.total_tasks == 3
        assert metrics.tasks_completed == 2
        assert metrics.total_tokens == 1500
        assert metrics.prompt_tokens == 1200
        assert metrics.completion_tokens == 300
        assert metrics.total_cost_usd == 0.015
        assert metrics.deepeval_scores["completeness"] == 0.85
        assert metrics.custom["latency_avg"] == 200.0

    @staticmethod
    def test_success_rate_calculation() -> None:
        """Test success_rate property calculation."""
        metrics = ConversationMetrics(
            total_turns=10,
            total_tasks=4,
            tasks_completed=3,
        )
        assert metrics.success_rate == 0.75

    @staticmethod
    def test_success_rate_zero_tasks() -> None:
        """Test success_rate with zero tasks."""
        metrics = ConversationMetrics(
            total_turns=0,
            total_tasks=0,
            tasks_completed=0,
        )
        assert metrics.success_rate == 0.0

    @staticmethod
    def test_success_rate_all_completed() -> None:
        """Test success_rate when all tasks completed."""
        metrics = ConversationMetrics(
            total_turns=5,
            total_tasks=2,
            tasks_completed=2,
        )
        assert metrics.success_rate == 1.0

    @staticmethod
    def test_conversation_metrics_defaults() -> None:
        """Test ConversationMetrics with default values."""
        metrics = ConversationMetrics(
            total_turns=5,
            total_tasks=2,
            tasks_completed=1,
        )

        assert metrics.total_tokens == 0
        assert metrics.prompt_tokens == 0
        assert metrics.completion_tokens == 0
        assert metrics.total_cost_usd == 0.0
        assert metrics.deepeval_scores == {}
        assert metrics.custom == {}


class TestSimulationStatus:
    """Tests for SimulationStatus enum."""

    @staticmethod
    def test_status_values() -> None:
        """Test SimulationStatus enum values."""
        assert SimulationStatus.RUNNING.value == "running"
        assert SimulationStatus.COMPLETED.value == "completed"
        assert SimulationStatus.FAILED.value == "failed"
        assert SimulationStatus.TIMEOUT.value == "timeout"

    @staticmethod
    def test_status_from_string() -> None:
        """Test creating SimulationStatus from string."""
        assert SimulationStatus("completed") == SimulationStatus.COMPLETED
        assert SimulationStatus("failed") == SimulationStatus.FAILED


class TestSimulationResult:
    """Tests for SimulationResult dataclass."""

    @staticmethod
    @pytest.fixture
    def sample_turn_results() -> list[TurnResult]:
        """Create sample turn results."""
        return [
            TurnResult(
                turn_index=1,
                task_index=0,
                user_message="Find hotels in Warsaw",
                assistant_message="I found 3 hotels in Warsaw.",
                tool_calls=[{"name": "search_hotels", "arguments": {"city": "Warsaw"}, "result": "3 hotels"}],
                task_completed=True,
                task_completed_reason="Hotels found",
                token_usage={"total": 100, "prompt": 80, "completion": 20},
            ),
            TurnResult(
                turn_index=2,
                task_index=1,
                user_message="Book the first one",
                assistant_message="Booking confirmed.",
                tool_calls=[{"name": "book_hotel", "arguments": {"hotel_id": "1"}, "result": "confirmed"}],
                task_completed=True,
                task_completed_reason="Booking done",
                token_usage={"total": 80, "prompt": 60, "completion": 20},
            ),
        ]

    @staticmethod
    @pytest.fixture
    def sample_task_results() -> list[TaskResult]:
        """Create sample task results."""
        return [
            TaskResult(
                task_index=0,
                description="Find hotels",
                expected_result="List of hotels",
                completed=True,
                turns_taken=1,
                final_reason="Hotels found",
            ),
            TaskResult(
                task_index=1,
                description="Book hotel",
                expected_result="Booking confirmation",
                completed=True,
                turns_taken=1,
                final_reason="Booking done",
            ),
        ]

    @staticmethod
    @pytest.fixture
    def sample_metrics() -> ConversationMetrics:
        """Create sample metrics."""
        return ConversationMetrics(
            total_turns=2,
            total_tasks=2,
            tasks_completed=2,
            total_tokens=180,
            prompt_tokens=140,
            completion_tokens=40,
            total_cost_usd=0.002,
            deepeval_scores={"completeness": 0.95},
        )

    @staticmethod
    @pytest.fixture
    def sample_result(
        sample_turn_results: list[TurnResult],
        sample_task_results: list[TaskResult],
        sample_metrics: ConversationMetrics,
    ) -> SimulationResult:
        """Create a sample SimulationResult."""
        return SimulationResult(
            scenario_name="Hotel Booking",
            start_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
            status=SimulationStatus.COMPLETED,
            agent_model="gpt-4o-mini",
            simulated_user_model="gpt-4o-mini",
            checker_model="gpt-4o-mini",
            personality="Friendly",
            turns=sample_turn_results,
            tasks=sample_task_results,
            metrics=sample_metrics,
        )

    @staticmethod
    def test_simulation_result_creation(sample_result: SimulationResult) -> None:
        """Test creating a SimulationResult."""
        assert sample_result.scenario_name == "Hotel Booking"
        assert sample_result.status == SimulationStatus.COMPLETED
        assert sample_result.agent_model == "gpt-4o-mini"
        assert sample_result.personality == "Friendly"
        assert len(sample_result.turns) == 2
        assert len(sample_result.tasks) == 2
        assert sample_result.metrics is not None
        assert sample_result.metrics.success_rate == 1.0
        assert sample_result.error is None

    @staticmethod
    def test_simulation_result_with_error() -> None:
        """Test SimulationResult with error."""
        result = SimulationResult(
            scenario_name="Test",
            start_time=datetime.now(timezone.utc),
            status=SimulationStatus.FAILED,
            error="Connection timeout",
        )

        assert result.status == SimulationStatus.FAILED
        assert result.error == "Connection timeout"
        assert result.turns == []
        assert result.tasks == []
        assert result.metrics is None

    @staticmethod
    def test_to_dict(sample_result: SimulationResult) -> None:
        """Test to_dict serialization."""
        data = sample_result.to_dict()

        assert data["scenario_name"] == "Hotel Booking"
        assert data["status"] == "completed"
        assert data["agent_model"] == "gpt-4o-mini"
        assert data["personality"] == "Friendly"
        assert data["start_time"] == "2024-01-15T10:00:00+00:00"
        assert data["end_time"] == "2024-01-15T10:05:00+00:00"
        assert len(data["turns"]) == 2
        assert len(data["tasks"]) == 2
        assert data["metrics"]["total_turns"] == 2
        assert data["metrics"]["success_rate"] == 1.0

    @staticmethod
    def test_to_dict_with_none_end_time() -> None:
        """Test to_dict with None end_time."""
        result = SimulationResult(
            scenario_name="Test",
            start_time=datetime.now(timezone.utc),
            status=SimulationStatus.RUNNING,
        )

        data = result.to_dict()
        assert data["end_time"] is None

    @staticmethod
    def test_from_dict(sample_result: SimulationResult) -> None:
        """Test from_dict deserialization."""
        data = sample_result.to_dict()
        loaded = SimulationResult.from_dict(data)

        assert loaded.scenario_name == sample_result.scenario_name
        assert loaded.status == sample_result.status
        assert loaded.agent_model == sample_result.agent_model
        assert loaded.personality == sample_result.personality
        assert len(loaded.turns) == len(sample_result.turns)
        assert len(loaded.tasks) == len(sample_result.tasks)
        assert loaded.metrics is not None
        assert sample_result.metrics is not None
        assert loaded.metrics.total_turns == sample_result.metrics.total_turns
        assert loaded.metrics.success_rate == sample_result.metrics.success_rate

    @staticmethod
    def test_from_dict_roundtrip(sample_result: SimulationResult) -> None:
        """Test that to_dict -> from_dict preserves data."""
        data = sample_result.to_dict()
        loaded = SimulationResult.from_dict(data)
        data_again = loaded.to_dict()

        assert data == data_again

    @staticmethod
    def test_from_dict_minimal() -> None:
        """Test from_dict with minimal data."""
        data = {
            "scenario_name": "Test",
            "start_time": "2024-01-15T10:00:00+00:00",
            "status": "running",
        }

        result = SimulationResult.from_dict(data)
        assert result.scenario_name == "Test"
        assert result.status == SimulationStatus.RUNNING
        assert result.turns == []
        assert result.tasks == []
        assert result.metrics is None

    @staticmethod
    def test_from_dict_with_metrics() -> None:
        """Test from_dict with metrics."""
        data = {
            "scenario_name": "Test",
            "start_time": "2024-01-15T10:00:00+00:00",
            "status": "completed",
            "metrics": {
                "total_turns": 5,
                "total_tasks": 2,
                "tasks_completed": 1,
                "total_tokens": 500,
                "prompt_tokens": 400,
                "completion_tokens": 100,
                "total_cost_usd": 0.005,
                "deepeval_scores": {"completeness": 0.8},
                "custom": {},
            },
        }

        result = SimulationResult.from_dict(data)
        assert result.metrics is not None
        assert result.metrics.total_turns == 5
        assert result.metrics.success_rate == 0.5
        assert result.metrics.deepeval_scores["completeness"] == 0.8
