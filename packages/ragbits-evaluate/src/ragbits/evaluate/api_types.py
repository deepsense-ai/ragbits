"""API types for the evaluation UI endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ragbits.evaluate.agent_simulation.results import SimulationStatus


class TaskDetail(BaseModel):
    """Task details for scenario display and editing."""

    task: str
    expected_result: str
    expected_tools: list[str] | None = None


class ScenarioSummary(BaseModel):
    """Summary of a scenario for listing."""

    name: str
    num_tasks: int


class ScenarioDetail(BaseModel):
    """Full scenario details for viewing and editing."""

    name: str
    tasks: list[TaskDetail]


class EvalConfigResponse(BaseModel):
    """Configuration response with available scenarios."""

    available_scenarios: list[ScenarioSummary]
    scenarios_dir: str


class RunEvaluationConfig(BaseModel):
    """Configuration for running a simulation via API.

    This is the frontend-facing config model with validation constraints.
    """

    max_turns_scenario: int = Field(default=15, ge=1, le=100)
    max_turns_task: int | None = Field(default=4, ge=1, le=50)
    sim_user_model_name: str | None = None
    checker_model_name: str | None = None
    default_model: str = "gpt-4o-mini"


class RunEvaluationRequest(BaseModel):
    """Request to start an evaluation run."""

    scenario_names: list[str] = Field(..., min_length=1)
    config: RunEvaluationConfig = Field(default_factory=RunEvaluationConfig)


class RunStartResponse(BaseModel):
    """Response when starting an evaluation run."""

    run_id: str
    scenarios: list[str]


class ProgressUpdate(BaseModel):
    """Base progress update for SSE streaming."""

    type: str
    run_id: str
    scenario_name: str


class StatusProgressUpdate(ProgressUpdate):
    """Status change progress update."""

    type: str = "status"
    status: SimulationStatus
    current_turn: int | None = None
    current_task_index: int | None = None
    current_task: str | None = None


class TurnProgressUpdate(ProgressUpdate):
    """Turn completion progress update."""

    type: str = "turn"
    turn_index: int
    task_index: int
    user_message: str
    assistant_message: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    task_completed: bool = False
    task_completed_reason: str = ""


class TaskCompleteUpdate(ProgressUpdate):
    """Task completion progress update."""

    type: str = "task_complete"
    task_index: int
    task_description: str
    turns_taken: int
    reason: str


class CompletionUpdate(ProgressUpdate):
    """Scenario completion progress update."""

    type: str = "complete"
    result_id: str
    status: SimulationStatus
    success_rate: float
    total_turns: int
    total_tasks: int
    tasks_completed: int


class ErrorUpdate(ProgressUpdate):
    """Error progress update."""

    type: str = "error"
    error: str


class SourceReference(BaseModel):
    """A source/reference document from the chat response."""

    title: str
    content: str
    url: str | None = None


class SourceUpdate(ProgressUpdate):
    """Source/reference document progress update."""

    type: str = "source"
    turn_index: int
    task_index: int
    source: SourceReference


class ResponseChunkUpdate(ProgressUpdate):
    """Real-time ChatInterface response chunk progress update.

    Streams raw response chunks from the ChatInterface as they arrive,
    enabling real-time visibility into all response types.
    """

    type: str = "response_chunk"
    turn_index: int
    task_index: int
    chunk_type: str  # e.g., "text", "reference", "tool_call", "usage", "live_update", etc.
    chunk_data: dict[str, Any]


class ResultSummary(BaseModel):
    """Summary of an evaluation result for listing."""

    result_id: str
    scenario_name: str
    timestamp: datetime
    status: SimulationStatus
    tasks_completed: int
    total_tasks: int
    success_rate: float
    total_turns: int
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class ResultsListResponse(BaseModel):
    """Response for listing evaluation results."""

    results: list[ResultSummary]
    total: int


class TestPersonaRequest(BaseModel):
    """Request to test how a persona would ask a task."""

    task: str
    expected_result: str | None = None
    persona: str | None = None
    scenario_name: str | None = None
    task_index: int | None = None
    model: str | None = None


class TestPersonaResponse(BaseModel):
    """Response with the generated persona message."""

    message: str
    persona: str | None = None
    model: str
