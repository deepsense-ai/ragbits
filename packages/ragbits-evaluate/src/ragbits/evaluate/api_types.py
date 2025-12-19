"""API types for the evaluation UI endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ragbits.evaluate.agent_simulation.results import SimulationStatus


class TaskDetail(BaseModel):
    """Task details for scenario display and editing."""

    task: str
    checkers: list[dict[str, Any]] = Field(default_factory=list)
    checker_mode: str = "all"


class ScenarioSummary(BaseModel):
    """Summary of a scenario for listing."""

    name: str
    num_tasks: int
    group: str | None = None


class ScenarioFileSummary(BaseModel):
    """Summary of a scenario file with its scenarios."""

    filename: str
    group: str | None = None
    scenarios: list[ScenarioSummary]


class ScenarioDetail(BaseModel):
    """Full scenario details for viewing and editing."""

    name: str
    tasks: list[TaskDetail]
    group: str | None = None


class EvalConfigResponse(BaseModel):
    """Configuration response with available scenarios."""

    available_scenarios: list[ScenarioSummary]
    scenario_files: list[ScenarioFileSummary] = Field(default_factory=list)
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
    """Request to start an evaluation run.

    If personas is provided, creates a matrix run: each scenario × each persona.
    If personas is empty or None, runs each scenario once without a persona.
    """

    scenario_names: list[str] = Field(..., min_length=1)
    personas: list[str] | None = Field(default=None, description="Personas for matrix runs")
    config: RunEvaluationConfig = Field(default_factory=RunEvaluationConfig)


class RunStartResponse(BaseModel):
    """Response when starting an evaluation run."""

    run_id: str
    scenarios: list[str]


class ProgressUpdate(BaseModel):
    """Base progress update for SSE streaming."""

    type: str
    run_id: str
    scenario_run_id: str  # Unique ID for the scenario run (scenario + persona)
    scenario_name: str
    persona: str | None = None  # Persona used for this scenario run


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
    checkers: list[dict[str, Any]] = Field(default_factory=list)
    checker_mode: str = "all"


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
    persona: str | None = None
    scenario_name: str | None = None
    task_index: int | None = None
    model: str | None = None


class TestPersonaResponse(BaseModel):
    """Response with the generated persona message."""

    message: str
    persona: str | None = None
    model: str


class PersonaSummary(BaseModel):
    """Summary of a persona for listing."""

    name: str
    description: str


class PersonasListResponse(BaseModel):
    """Response for listing personas."""

    personas: list[PersonaSummary]
    total: int


class ScenarioRunSummary(BaseModel):
    """Summary of a single scenario within a batch run."""

    id: str  # Unique ID for this scenario run (scenario + persona + run_id)
    scenario_name: str
    persona: str | None = None
    status: SimulationStatus
    start_time: datetime
    end_time: datetime | None = None
    total_turns: int = 0
    total_tasks: int = 0
    tasks_completed: int = 0
    success_rate: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    error: str | None = None


class SimulationRunSummary(BaseModel):
    """Summary of a batch simulation run containing multiple scenarios."""

    id: str
    timestamp: datetime
    version: str = "current"
    status: SimulationStatus
    scenario_runs: list[ScenarioRunSummary]
    total_scenarios: int
    completed_scenarios: int = 0
    failed_scenarios: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    overall_success_rate: float = 0.0


class SimulationRunsListResponse(BaseModel):
    """Response for listing simulation runs."""

    runs: list[SimulationRunSummary]
    total: int


class CheckerResultItemResponse(BaseModel):
    """Result of a single checker evaluation."""

    type: str
    completed: bool
    reason: str


class TurnResultResponse(BaseModel):
    """Turn result with conversation data."""

    turn_index: int
    task_index: int
    user_message: str
    assistant_message: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    task_completed: bool = False
    task_completed_reason: str = ""
    token_usage: dict[str, int] | None = None
    latency_ms: float | None = None
    checkers: list[CheckerResultItemResponse] = Field(default_factory=list)
    checker_mode: str = "all"


class TaskResultResponse(BaseModel):
    """Task result."""

    task_index: int
    description: str


class ResponseChunkResponse(BaseModel):
    """Response chunk from ChatInterface stream."""

    turn_index: int
    task_index: int
    chunk_index: int
    chunk_type: str
    chunk_data: dict[str, Any]


class ScenarioRunDetail(BaseModel):
    """Full scenario run details including turns and tasks."""

    id: str  # Unique ID for this scenario run
    scenario_name: str
    persona: str | None = None
    status: SimulationStatus
    start_time: datetime
    end_time: datetime | None = None
    turns: list[TurnResultResponse] = Field(default_factory=list)
    tasks: list[TaskResultResponse] = Field(default_factory=list)
    response_chunks: list[ResponseChunkResponse] = Field(default_factory=list)
    metrics: dict[str, Any] | None = None
    error: str | None = None


class SimulationRunDetail(BaseModel):
    """Full simulation run details."""

    id: str
    timestamp: datetime
    version: str = "current"
    status: SimulationStatus
    scenario_runs: list[ScenarioRunDetail]
    total_scenarios: int
    completed_scenarios: int = 0
    failed_scenarios: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    overall_success_rate: float = 0.0
