"""Result models for agent simulation scenarios."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SimulationStatus(str, Enum):
    """Status of a simulation run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TurnResult:
    """Result of a single conversation turn."""

    turn_index: int
    task_index: int
    user_message: str
    assistant_message: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    task_completed: bool = False
    task_completed_reason: str = ""
    token_usage: dict[str, int] | None = None
    latency_ms: float | None = None


@dataclass
class TaskResult:
    """Result of a single task within the scenario."""

    task_index: int
    description: str
    expected_result: str | None
    completed: bool
    turns_taken: int
    final_reason: str


@dataclass
class ConversationMetrics:
    """Aggregate metrics for the conversation."""

    total_turns: int
    total_tasks: int
    tasks_completed: int
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    deepeval_scores: dict[str, float] = field(default_factory=dict)
    custom: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate task success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.tasks_completed / self.total_tasks


@dataclass
class SimulationResult:
    """Complete result for a scenario simulation."""

    # Metadata
    scenario_name: str
    start_time: datetime
    status: SimulationStatus

    # Detailed data
    turns: list[TurnResult] = field(default_factory=list)
    tasks: list[TaskResult] = field(default_factory=list)
    metrics: ConversationMetrics | None = None

    # Optional metadata
    end_time: datetime | None = None
    agent_model: str | None = None
    simulated_user_model: str | None = None
    checker_model: str | None = None
    personality: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "scenario_name": self.scenario_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "agent_model": self.agent_model,
            "simulated_user_model": self.simulated_user_model,
            "checker_model": self.checker_model,
            "personality": self.personality,
            "error": self.error,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "task_index": t.task_index,
                    "user_message": t.user_message,
                    "assistant_message": t.assistant_message,
                    "tool_calls": t.tool_calls,
                    "task_completed": t.task_completed,
                    "task_completed_reason": t.task_completed_reason,
                    "token_usage": t.token_usage,
                    "latency_ms": t.latency_ms,
                }
                for t in self.turns
            ],
            "tasks": [
                {
                    "task_index": t.task_index,
                    "description": t.description,
                    "expected_result": t.expected_result,
                    "completed": t.completed,
                    "turns_taken": t.turns_taken,
                    "final_reason": t.final_reason,
                }
                for t in self.tasks
            ],
            "metrics": {
                "total_turns": self.metrics.total_turns,
                "total_tasks": self.metrics.total_tasks,
                "tasks_completed": self.metrics.tasks_completed,
                "success_rate": self.metrics.success_rate,
                "total_tokens": self.metrics.total_tokens,
                "prompt_tokens": self.metrics.prompt_tokens,
                "completion_tokens": self.metrics.completion_tokens,
                "total_cost_usd": self.metrics.total_cost_usd,
                "deepeval_scores": self.metrics.deepeval_scores,
                "custom": self.metrics.custom,
            }
            if self.metrics
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationResult":
        """Create from dictionary."""
        turns = [
            TurnResult(
                turn_index=t["turn_index"],
                task_index=t["task_index"],
                user_message=t["user_message"],
                assistant_message=t["assistant_message"],
                tool_calls=t.get("tool_calls", []),
                task_completed=t.get("task_completed", False),
                task_completed_reason=t.get("task_completed_reason", ""),
                token_usage=t.get("token_usage"),
                latency_ms=t.get("latency_ms"),
            )
            for t in data.get("turns", [])
        ]

        tasks = [
            TaskResult(
                task_index=t["task_index"],
                description=t["description"],
                expected_result=t.get("expected_result"),
                completed=t["completed"],
                turns_taken=t["turns_taken"],
                final_reason=t["final_reason"],
            )
            for t in data.get("tasks", [])
        ]

        metrics_data = data.get("metrics")
        metrics = None
        if metrics_data:
            metrics = ConversationMetrics(
                total_turns=metrics_data["total_turns"],
                total_tasks=metrics_data["total_tasks"],
                tasks_completed=metrics_data["tasks_completed"],
                total_tokens=metrics_data.get("total_tokens", 0),
                prompt_tokens=metrics_data.get("prompt_tokens", 0),
                completion_tokens=metrics_data.get("completion_tokens", 0),
                total_cost_usd=metrics_data.get("total_cost_usd", 0.0),
                deepeval_scores=metrics_data.get("deepeval_scores", {}),
                custom=metrics_data.get("custom", {}),
            )

        return cls(
            scenario_name=data["scenario_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            status=SimulationStatus(data["status"]),
            agent_model=data.get("agent_model"),
            simulated_user_model=data.get("simulated_user_model"),
            checker_model=data.get("checker_model"),
            personality=data.get("personality"),
            error=data.get("error"),
            turns=turns,
            tasks=tasks,
            metrics=metrics,
        )
