"""Execution manager for running and tracking evaluation simulations."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ragbits.evaluate.agent_simulation.results import ResponseChunk, SimulationResult, SimulationStatus
from ragbits.evaluate.api_types import (
    CompletionUpdate,
    ErrorUpdate,
    ProgressUpdate,
    ResponseChunkUpdate,
    ResultSummary,
    SimulationRunDetail,
    SimulationRunSummary,
    StatusProgressUpdate,
    TaskCompleteUpdate,
    TurnProgressUpdate,
)

if TYPE_CHECKING:
    from ragbits.evaluate.stores.base import EvalReportStore

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[ProgressUpdate], Awaitable[None]]


class ExecutionManager:
    """Manages parallel simulation execution and result persistence."""

    def __init__(self, store: EvalReportStore | Path | None = None) -> None:
        """Initialize the execution manager.

        Args:
            store: Storage backend for evaluation results. Can be:
                - EvalReportStore instance for custom storage
                - Path for file-based storage (backward compatibility)
                - None to use default file-based storage in ./eval_results
        """
        from ragbits.evaluate.stores import FileEvalReportStore

        if store is None:
            self.store: EvalReportStore = FileEvalReportStore(Path("./eval_results"))
        elif isinstance(store, Path):
            self.store = FileEvalReportStore(store)
        else:
            self.store = store

        # Active runs: run_id -> dict with queue, tasks, start_time
        self._active_runs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def generate_run_id() -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique = uuid.uuid4().hex[:8]
        return f"run_{timestamp}_{unique}"

    @staticmethod
    def generate_scenario_run_id(scenario_name: str, persona: str | None = None) -> str:
        """Generate a unique scenario run ID.

        Args:
            scenario_name: Name of the scenario.
            persona: Optional persona name.

        Returns:
            Unique scenario run ID.
        """
        safe_scenario = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario_name)
        safe_persona = ""
        if persona:
            safe_persona = "_" + "".join(c if c.isalnum() or c in "-_" else "_" for c in persona)
        unique = uuid.uuid4().hex[:6]
        return f"sr_{safe_scenario}{safe_persona}_{unique}"

    def create_run(self, run_id: str, scenario_names: list[str]) -> asyncio.Queue[ProgressUpdate]:
        """Create a new run and return its progress queue.

        Args:
            run_id: Unique identifier for this run.
            scenario_names: List of scenario names being executed.

        Returns:
            Queue for receiving progress updates.
        """
        queue: asyncio.Queue[ProgressUpdate] = asyncio.Queue()
        self._active_runs[run_id] = {
            "queue": queue,
            "scenarios": scenario_names,
            "start_time": datetime.now(timezone.utc),
            "tasks": {},
            "completed": set(),
            # Scenario run registry: scenario_run_id -> {scenario_name, persona, ...}
            "scenario_runs": {},
            # Buffer all events per scenario_run_id for late subscribers
            "event_buffer": {},
        }
        return queue

    def register_scenario_run(
        self,
        run_id: str,
        scenario_name: str,
        persona: str | None = None,
    ) -> str:
        """Register a scenario run and get its unique ID.

        Args:
            run_id: Run identifier.
            scenario_name: Name of the scenario.
            persona: Optional persona name.

        Returns:
            Unique scenario run ID.
        """
        run = self._active_runs.get(run_id)
        if not run:
            raise ValueError(f"Run '{run_id}' not found")

        scenario_run_id = self.generate_scenario_run_id(scenario_name, persona)
        run["scenario_runs"][scenario_run_id] = {
            "scenario_name": scenario_name,
            "persona": persona,
            "start_time": datetime.now(timezone.utc),
        }
        run["event_buffer"][scenario_run_id] = []
        return scenario_run_id

    def get_scenario_run_buffer(self, run_id: str, scenario_run_id: str) -> list[ProgressUpdate]:
        """Get buffered events for a scenario run.

        Args:
            run_id: Run identifier.
            scenario_run_id: Scenario run identifier.

        Returns:
            List of buffered progress updates.
        """
        run = self._active_runs.get(run_id)
        if not run:
            return []
        return run["event_buffer"].get(scenario_run_id, [])

    def get_progress_queue(self, run_id: str) -> asyncio.Queue[ProgressUpdate] | None:
        """Get the progress queue for a run.

        Args:
            run_id: Run identifier.

        Returns:
            Progress queue if run exists, None otherwise.
        """
        run = self._active_runs.get(run_id)
        return run["queue"] if run else None

    def is_run_active(self, run_id: str) -> bool:
        """Check if a run is still active.

        Args:
            run_id: Run identifier.

        Returns:
            True if run is active.
        """
        return run_id in self._active_runs

    def mark_scenario_complete(self, run_id: str, scenario_name: str) -> bool:
        """Mark a scenario as complete and check if run is finished.

        Args:
            run_id: Run identifier.
            scenario_name: Name of completed scenario.

        Returns:
            True if all scenarios in the run are complete.
        """
        run = self._active_runs.get(run_id)
        if not run:
            return True

        run["completed"].add(scenario_name)
        return len(run["completed"]) >= len(run["scenarios"])

    def cleanup_run(self, run_id: str) -> None:
        """Clean up a completed run.

        Args:
            run_id: Run identifier to clean up.
        """
        if run_id in self._active_runs:
            del self._active_runs[run_id]

    async def emit_progress(self, run_id: str, update: ProgressUpdate) -> None:
        """Emit a progress update to the run's queue and buffer it.

        Args:
            run_id: Run identifier.
            update: Progress update to emit.
        """
        run = self._active_runs.get(run_id)
        if not run:
            return

        # Buffer the event for the scenario run
        scenario_run_id = update.scenario_run_id
        if scenario_run_id in run["event_buffer"]:
            run["event_buffer"][scenario_run_id].append(update)

        # Also emit to the queue for real-time streaming
        queue = run.get("queue")
        if queue:
            await queue.put(update)

    async def stream_progress(self, run_id: str) -> AsyncGenerator[ProgressUpdate, None]:
        """Stream progress updates for a run.

        Args:
            run_id: Run identifier.

        Yields:
            Progress updates as they occur.
        """
        queue = self.get_progress_queue(run_id)
        if not queue:
            return

        while True:
            try:
                # Use timeout to allow checking if run is still active
                update = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield update

                # Check if this is a terminal update
                if isinstance(update, CompletionUpdate | ErrorUpdate) and self.mark_scenario_complete(
                    run_id, update.scenario_name
                ):
                    # All scenarios complete, clean up
                    self.cleanup_run(run_id)
                    return
            except TimeoutError:
                # Check if run is still active
                if not self.is_run_active(run_id):
                    return
                continue
            except asyncio.CancelledError:
                return

    async def save_result(
        self, run_id: str, scenario_run_id: str, scenario_name: str, result: SimulationResult
    ) -> str:
        """Save a simulation result.

        Args:
            run_id: Run identifier.
            scenario_run_id: Unique scenario run identifier.
            scenario_name: Name of the scenario.
            result: Simulation result to save.

        Returns:
            Result ID for later retrieval.
        """
        # Collect response chunks from the event buffer
        buffered_events = self.get_scenario_run_buffer(run_id, scenario_run_id)
        buffered_chunks = []
        for event in buffered_events:
            if event.type == "response_chunk":
                buffered_chunks.append(
                    ResponseChunk(
                        turn_index=event.turn_index,
                        task_index=event.task_index,
                        chunk_index=0,  # Will be re-indexed by the store
                        chunk_type=event.chunk_type,
                        chunk_data=event.chunk_data,
                    )
                )

        return await self.store.save_result(
            run_id=run_id,
            scenario_run_id=scenario_run_id,
            scenario_name=scenario_name,
            result=result,
            buffered_chunks=buffered_chunks if buffered_chunks else None,
        )

    async def list_results(self, limit: int = 50, offset: int = 0) -> tuple[list[ResultSummary], int]:
        """List evaluation results with pagination.

        Args:
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            Tuple of (results list, total count).
        """
        return await self.store.list_results(limit=limit, offset=offset)

    async def load_result(self, result_id: str) -> SimulationResult | None:
        """Load a simulation result.

        Args:
            result_id: Result identifier.

        Returns:
            SimulationResult if found, None otherwise.
        """
        return await self.store.load_result(result_id)

    async def delete_result(self, result_id: str) -> bool:
        """Delete a simulation result.

        Args:
            result_id: Result identifier.

        Returns:
            True if deleted, False if not found.
        """
        return await self.store.delete_result(result_id)

    async def list_runs(self, limit: int = 50, offset: int = 0) -> tuple[list[SimulationRunSummary], int]:
        """List simulation runs (batch runs grouped by run_id).

        Args:
            limit: Maximum number of runs to return.
            offset: Number of runs to skip.

        Returns:
            Tuple of (runs list, total count).
        """
        return await self.store.list_runs(limit=limit, offset=offset)

    async def get_run(self, run_id: str) -> SimulationRunDetail | None:
        """Get full details for a simulation run.

        Args:
            run_id: Run identifier.

        Returns:
            SimulationRunDetail if found, None otherwise.
        """
        return await self.store.get_run(run_id)


def create_progress_callback(
    run_id: str,
    scenario_run_id: str,
    scenario_name: str,
    execution_manager: ExecutionManager,
    persona: str | None = None,
) -> ProgressCallback:
    """Create a progress callback for use with run_simulation.

    Args:
        run_id: Run identifier.
        scenario_run_id: Unique scenario run identifier (includes persona if any).
        scenario_name: Name of the scenario being run.
        execution_manager: Execution manager instance.
        persona: Optional persona name for this scenario run.

    Returns:
        Async callback function for progress updates.
    """

    async def callback(
        event_type: str,
        **kwargs: Any,
    ) -> None:
        """Progress callback for simulation events."""
        update: ProgressUpdate

        if event_type == "status":
            update = StatusProgressUpdate(
                run_id=run_id,
                scenario_run_id=scenario_run_id,
                scenario_name=scenario_name,
                persona=persona,
                status=kwargs.get("status", SimulationStatus.RUNNING),
                current_turn=kwargs.get("current_turn"),
                current_task_index=kwargs.get("current_task_index"),
                current_task=kwargs.get("current_task"),
            )
        elif event_type == "turn":
            update = TurnProgressUpdate(
                run_id=run_id,
                scenario_run_id=scenario_run_id,
                scenario_name=scenario_name,
                persona=persona,
                turn_index=kwargs.get("turn_index", 0),
                task_index=kwargs.get("task_index", 0),
                user_message=kwargs.get("user_message", ""),
                assistant_message=kwargs.get("assistant_message", ""),
                tool_calls=kwargs.get("tool_calls", []),
                task_completed=kwargs.get("task_completed", False),
                task_completed_reason=kwargs.get("task_completed_reason", ""),
                checkers=kwargs.get("checkers", []),
                checker_mode=kwargs.get("checker_mode", "all"),
            )
        elif event_type == "task_complete":
            update = TaskCompleteUpdate(
                run_id=run_id,
                scenario_run_id=scenario_run_id,
                scenario_name=scenario_name,
                persona=persona,
                task_index=kwargs.get("task_index", 0),
                task_description=kwargs.get("task_description", ""),
                turns_taken=kwargs.get("turns_taken", 0),
                reason=kwargs.get("reason", ""),
            )
        elif event_type == "complete":
            update = CompletionUpdate(
                run_id=run_id,
                scenario_run_id=scenario_run_id,
                scenario_name=scenario_name,
                persona=persona,
                result_id=kwargs.get("result_id", ""),
                status=kwargs.get("status", SimulationStatus.COMPLETED),
                success_rate=kwargs.get("success_rate", 0.0),
                total_turns=kwargs.get("total_turns", 0),
                total_tasks=kwargs.get("total_tasks", 0),
                tasks_completed=kwargs.get("tasks_completed", 0),
            )
        elif event_type == "error":
            update = ErrorUpdate(
                run_id=run_id,
                scenario_run_id=scenario_run_id,
                scenario_name=scenario_name,
                persona=persona,
                error=kwargs.get("error", "Unknown error"),
            )
        elif event_type == "response_chunk":
            update = ResponseChunkUpdate(
                run_id=run_id,
                scenario_run_id=scenario_run_id,
                scenario_name=scenario_name,
                persona=persona,
                turn_index=kwargs.get("turn_index", 0),
                task_index=kwargs.get("task_index", 0),
                chunk_type=kwargs.get("chunk_type", "unknown"),
                chunk_data=kwargs.get("chunk_data", {}),
            )
        else:
            return

        await execution_manager.emit_progress(run_id, update)

    return callback
