"""Execution manager for running and tracking evaluation simulations."""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ragbits.evaluate.agent_simulation.results import SimulationResult, SimulationStatus
from ragbits.evaluate.api_types import (
    CompletionUpdate,
    ErrorUpdate,
    ProgressUpdate,
    ResultSummary,
    StatusProgressUpdate,
    TaskCompleteUpdate,
    TurnProgressUpdate,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[ProgressUpdate], Awaitable[None]]


class ExecutionManager:
    """Manages parallel simulation execution and result persistence."""

    def __init__(self, results_dir: Path) -> None:
        """Initialize the execution manager.

        Args:
            results_dir: Directory for storing evaluation results as JSON files.
        """
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Active runs: run_id -> dict with queue, tasks, start_time
        self._active_runs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def generate_run_id() -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique = uuid.uuid4().hex[:8]
        return f"run_{timestamp}_{unique}"

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
        }
        return queue

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
        """Emit a progress update to the run's queue.

        Args:
            run_id: Run identifier.
            update: Progress update to emit.
        """
        queue = self.get_progress_queue(run_id)
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

    def save_result(self, run_id: str, scenario_name: str, result: SimulationResult) -> str:
        """Save a simulation result to disk.

        Args:
            run_id: Run identifier.
            scenario_name: Name of the scenario.
            result: Simulation result to save.

        Returns:
            Result ID (filename without extension).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario_name)
        result_id = f"result_{timestamp}_{safe_name}"

        result_path = self.results_dir / f"{result_id}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved result to {result_path}")
        return result_id

    def list_results(self, limit: int = 50, offset: int = 0) -> tuple[list[ResultSummary], int]:
        """List evaluation results with pagination.

        Args:
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            Tuple of (results list, total count).
        """
        result_files = sorted(
            self.results_dir.glob("result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        total = len(result_files)
        paginated = result_files[offset : offset + limit]

        summaries = []
        for path in paginated:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                metrics = data.get("metrics", {})
                summaries.append(
                    ResultSummary(
                        result_id=path.stem,
                        scenario_name=data.get("scenario_name", "Unknown"),
                        timestamp=datetime.fromisoformat(
                            data.get("start_time", datetime.now(timezone.utc).isoformat())
                        ),
                        status=SimulationStatus(data.get("status", "completed")),
                        tasks_completed=metrics.get("tasks_completed", 0),
                        total_tasks=metrics.get("total_tasks", 0),
                        success_rate=metrics.get("success_rate", 0.0),
                        total_turns=metrics.get("total_turns", 0),
                        total_tokens=metrics.get("total_tokens", 0),
                        total_cost_usd=metrics.get("total_cost_usd", 0.0),
                    )
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse result file {path}: {e}")
                continue

        return summaries, total

    def load_result(self, result_id: str) -> SimulationResult | None:
        """Load a simulation result from disk.

        Args:
            result_id: Result identifier (filename without extension).

        Returns:
            SimulationResult if found, None otherwise.
        """
        result_path = self.results_dir / f"{result_id}.json"
        if not result_path.exists():
            return None

        try:
            with open(result_path, encoding="utf-8") as f:
                data = json.load(f)
            return SimulationResult.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to load result {result_id}: {e}")
            return None

    def delete_result(self, result_id: str) -> bool:
        """Delete a simulation result.

        Args:
            result_id: Result identifier.

        Returns:
            True if deleted, False if not found.
        """
        result_path = self.results_dir / f"{result_id}.json"
        if result_path.exists():
            result_path.unlink()
            return True
        return False


def create_progress_callback(
    run_id: str,
    scenario_name: str,
    execution_manager: ExecutionManager,
) -> ProgressCallback:
    """Create a progress callback for use with run_simulation.

    Args:
        run_id: Run identifier.
        scenario_name: Name of the scenario being run.
        execution_manager: Execution manager instance.

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
                scenario_name=scenario_name,
                status=kwargs.get("status", SimulationStatus.RUNNING),
                current_turn=kwargs.get("current_turn"),
                current_task_index=kwargs.get("current_task_index"),
                current_task=kwargs.get("current_task"),
            )
        elif event_type == "turn":
            update = TurnProgressUpdate(
                run_id=run_id,
                scenario_name=scenario_name,
                turn_index=kwargs.get("turn_index", 0),
                task_index=kwargs.get("task_index", 0),
                user_message=kwargs.get("user_message", ""),
                assistant_message=kwargs.get("assistant_message", ""),
                tool_calls=kwargs.get("tool_calls", []),
                task_completed=kwargs.get("task_completed", False),
                task_completed_reason=kwargs.get("task_completed_reason", ""),
            )
        elif event_type == "task_complete":
            update = TaskCompleteUpdate(
                run_id=run_id,
                scenario_name=scenario_name,
                task_index=kwargs.get("task_index", 0),
                task_description=kwargs.get("task_description", ""),
                turns_taken=kwargs.get("turns_taken", 0),
                reason=kwargs.get("reason", ""),
            )
        elif event_type == "complete":
            update = CompletionUpdate(
                run_id=run_id,
                scenario_name=scenario_name,
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
                scenario_name=scenario_name,
                error=kwargs.get("error", "Unknown error"),
            )
        else:
            return

        await execution_manager.emit_progress(run_id, update)

    return callback
