"""Result models for agent simulation scenarios."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ragbits.core.llms.base import Usage


class SimulationStatus(str, Enum):
    """Status of a simulation run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class CheckerResultItem:
    """Result of a single checker evaluation."""

    type: str
    completed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"type": self.type, "completed": self.completed, "reason": self.reason}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckerResultItem":
        """Create from dictionary."""
        return cls(
            type=data.get("type", data.get("checker_type", "unknown")),
            completed=data.get("completed", False),
            reason=data.get("reason", ""),
        )


@dataclass
class ResponseChunk:
    """A response chunk from the ChatInterface stream."""

    turn_index: int
    task_index: int
    chunk_index: int
    chunk_type: str
    chunk_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "turn_index": self.turn_index,
            "task_index": self.task_index,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "chunk_data": self.chunk_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResponseChunk":
        """Create from dictionary."""
        return cls(
            turn_index=data.get("turn_index", 0),
            task_index=data.get("task_index", 0),
            chunk_index=data.get("chunk_index", 0),
            chunk_type=data.get("chunk_type", "unknown"),
            chunk_data=data.get("chunk_data", {}),
        )


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
    token_usage: Usage = field(default_factory=Usage)
    latency_ms: float | None = None
    checkers: list[CheckerResultItem] = field(default_factory=list)
    checker_mode: str = "all"


@dataclass
class TaskResult:
    """Result of a single task within the scenario."""

    task_index: int
    description: str
    completed: bool
    turns_taken: int
    final_reason: str
    checkers: list[dict[str, Any]] = field(default_factory=list)
    checker_mode: str = "all"


@dataclass
class ConversationMetrics:
    """Aggregate metrics for the conversation.

    All metrics are stored in a single flat dictionary. Built-in metrics include:
    - total_turns: Number of conversation turns
    - total_tasks: Number of tasks in the scenario
    - tasks_completed: Number of successfully completed tasks
    - success_rate: Ratio of completed tasks
    - total_tokens, prompt_tokens, completion_tokens: Token usage
    - total_cost_usd: Estimated cost
    - latency_avg_ms, latency_min_ms, latency_max_ms: Response latency
    - tools_total_calls, tools_unique, tools_counts: Tool usage

    Additional metrics from custom collectors are merged into this dict.
    """

    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def total_turns(self) -> int:
        """Number of conversation turns."""
        return self.metrics.get("total_turns", 0)

    @property
    def total_tasks(self) -> int:
        """Number of tasks in scenario."""
        return self.metrics.get("total_tasks", 0)

    @property
    def tasks_completed(self) -> int:
        """Number of completed tasks."""
        return self.metrics.get("tasks_completed", 0)

    @property
    def success_rate(self) -> float:
        """Calculate task success rate."""
        return self.metrics.get("success_rate", 0.0)


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
    response_chunks: list[ResponseChunk] = field(default_factory=list)

    # Optional metadata
    end_time: datetime | None = None
    agent_model: str | None = None
    simulated_user_model: str | None = None
    checker_model: str | None = None
    persona: str | None = None
    error: str | None = None

    # Conversation context
    conversation_id: str | None = None
    final_state: dict[str, Any] = field(default_factory=dict)

    # Traces from the chat interface
    traces: list[dict[str, Any]] = field(default_factory=list)

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
            "persona": self.persona,
            "error": self.error,
            "conversation_id": self.conversation_id,
            "final_state": self.final_state,
            "response_chunks": [c.to_dict() for c in self.response_chunks],
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "task_index": t.task_index,
                    "user_message": t.user_message,
                    "assistant_message": t.assistant_message,
                    "tool_calls": t.tool_calls,
                    "task_completed": t.task_completed,
                    "task_completed_reason": t.task_completed_reason,
                    "token_usage": t.token_usage.model_dump() if t.token_usage else None,
                    "latency_ms": t.latency_ms,
                    "checkers": [c.to_dict() for c in t.checkers],
                    "checker_mode": t.checker_mode,
                }
                for t in self.turns
            ],
            "tasks": [
                {
                    "task_index": t.task_index,
                    "description": t.description,
                    "completed": t.completed,
                    "turns_taken": t.turns_taken,
                    "final_reason": t.final_reason,
                    "checkers": t.checkers,
                    "checker_mode": t.checker_mode,
                }
                for t in self.tasks
            ],
            "metrics": self.metrics.metrics if self.metrics else None,
            "traces": self.traces,
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
                checkers=[CheckerResultItem.from_dict(c) for c in t.get("checkers", [])],
                checker_mode=t.get("checker_mode", "all"),
            )
            for t in data.get("turns", [])
        ]

        tasks = [
            TaskResult(
                task_index=t["task_index"],
                description=t["description"],
                completed=t["completed"],
                turns_taken=t["turns_taken"],
                final_reason=t["final_reason"],
                checkers=t.get("checkers", []),
                checker_mode=t.get("checker_mode", "all"),
            )
            for t in data.get("tasks", [])
        ]

        metrics_data = data.get("metrics")
        metrics = ConversationMetrics(metrics=metrics_data) if metrics_data else None

        response_chunks = [ResponseChunk.from_dict(c) for c in data.get("response_chunks", [])]

        return cls(
            scenario_name=data["scenario_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            status=SimulationStatus(data["status"]),
            agent_model=data.get("agent_model"),
            simulated_user_model=data.get("simulated_user_model"),
            checker_model=data.get("checker_model"),
            persona=data.get("persona", data.get("personality")),  # backwards compat
            error=data.get("error"),
            conversation_id=data.get("conversation_id"),
            final_state=data.get("final_state", {}),
            turns=turns,
            tasks=tasks,
            metrics=metrics,
            response_chunks=response_chunks,
            traces=data.get("traces", []),
        )
