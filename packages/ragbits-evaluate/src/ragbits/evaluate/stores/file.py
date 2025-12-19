"""File-based evaluation report storage using JSON files."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ragbits.evaluate.agent_simulation.results import ResponseChunk, SimulationResult, SimulationStatus
from ragbits.evaluate.api_types import (
    CheckerResultItemResponse,
    ResponseChunkResponse,
    ResultSummary,
    ScenarioRunDetail,
    ScenarioRunSummary,
    SimulationRunDetail,
    SimulationRunSummary,
    TaskResultResponse,
    TurnResultResponse,
)
from ragbits.evaluate.stores.base import EvalReportStore

logger = logging.getLogger(__name__)


class FileEvalReportStore(EvalReportStore):
    """File-based storage for evaluation reports using JSON files.

    This is the default storage backend that maintains backward compatibility
    with the existing file-based approach.
    """

    def __init__(self, results_dir: Path | str) -> None:
        """Initialize the file-based store.

        Args:
            results_dir: Directory for storing evaluation results as JSON files.
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _generate_scenario_run_id(scenario_name: str, persona: str | None = None) -> str:
        """Generate a unique scenario run ID for old results without one."""
        import uuid

        safe_scenario = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario_name)
        safe_persona = ""
        if persona:
            safe_persona = "_" + "".join(c if c.isalnum() or c in "-_" else "_" for c in persona)
        unique = uuid.uuid4().hex[:6]
        return f"sr_{safe_scenario}{safe_persona}_{unique}"

    async def save_result(
        self,
        run_id: str,
        scenario_run_id: str,
        scenario_name: str,
        result: SimulationResult,
        buffered_chunks: list[ResponseChunk] | None = None,
    ) -> str:
        """Save a simulation result to disk.

        Args:
            run_id: Run identifier.
            scenario_run_id: Unique scenario run identifier.
            scenario_name: Name of the scenario.
            result: Simulation result to save.
            buffered_chunks: Optional response chunks from the event buffer.

        Returns:
            Result ID (filename without extension).
        """
        # Add buffered chunks to the result (skip text chunks)
        if buffered_chunks:
            chunk_index = len(result.response_chunks)
            for chunk in buffered_chunks:
                if chunk.chunk_type == "text":
                    continue
                result.response_chunks.append(
                    ResponseChunk(
                        turn_index=chunk.turn_index,
                        task_index=chunk.task_index,
                        chunk_index=chunk_index,
                        chunk_type=chunk.chunk_type,
                        chunk_data=chunk.chunk_data,
                    )
                )
                chunk_index += 1

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario_name)
        result_id = f"result_{timestamp}_{safe_name}"

        result_path = self.results_dir / f"{result_id}.json"
        result_data = result.to_dict()
        # Include run_id and scenario_run_id for grouping and identification
        result_data["run_id"] = run_id
        result_data["scenario_run_id"] = scenario_run_id

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, default=str)

        logger.info(f"Saved result to {result_path}")
        return result_id

    async def load_result(self, result_id: str) -> SimulationResult | None:
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

    async def delete_result(self, result_id: str) -> bool:
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

    async def list_results(self, limit: int = 50, offset: int = 0) -> tuple[list[ResultSummary], int]:
        """List evaluation results with pagination.

        Args:
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            Tuple of (results list, total count).
        """
        result_files = sorted(self.results_dir.glob("result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

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

    async def list_runs(self, limit: int = 50, offset: int = 0) -> tuple[list[SimulationRunSummary], int]:
        """List simulation runs (batch runs grouped by run_id).

        Args:
            limit: Maximum number of runs to return.
            offset: Number of runs to skip.

        Returns:
            Tuple of (runs list, total count).
        """
        result_files = sorted(self.results_dir.glob("result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        # Group results by run_id
        runs_map: dict[str, list[dict]] = {}
        for path in result_files:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                run_id = data.get("run_id", path.stem)  # Fallback to result_id if no run_id
                if run_id not in runs_map:
                    runs_map[run_id] = []
                runs_map[run_id].append(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse result file {path}: {e}")
                continue

        # Convert to SimulationRunSummary objects
        runs = []
        for run_id, results in runs_map.items():
            # Sort results by start_time
            results.sort(key=lambda r: r.get("start_time", ""), reverse=True)

            scenario_runs = []
            total_tokens = 0
            total_cost = 0.0
            completed = 0
            failed = 0

            for result in results:
                metrics = result.get("metrics") or {}
                status = SimulationStatus(result.get("status", "completed"))

                if status == SimulationStatus.COMPLETED:
                    completed += 1
                elif status in (SimulationStatus.FAILED, SimulationStatus.TIMEOUT):
                    failed += 1

                tokens = metrics.get("total_tokens", 0)
                cost = metrics.get("total_cost_usd", 0.0)
                total_tokens += tokens
                total_cost += cost

                # Get scenario_run_id, falling back to generated one for old results
                scenario_name = result.get("scenario_name", "Unknown")
                scenario_run_id = result.get("scenario_run_id", self._generate_scenario_run_id(scenario_name))

                scenario_runs.append(
                    ScenarioRunSummary(
                        id=scenario_run_id,
                        scenario_name=scenario_name,
                        persona=result.get("persona"),
                        status=status,
                        start_time=datetime.fromisoformat(
                            result.get("start_time", datetime.now(timezone.utc).isoformat())
                        ),
                        end_time=datetime.fromisoformat(result["end_time"]) if result.get("end_time") else None,
                        total_turns=metrics.get("total_turns", 0),
                        total_tasks=metrics.get("total_tasks", 0),
                        tasks_completed=metrics.get("tasks_completed", 0),
                        success_rate=metrics.get("success_rate", 0.0),
                        total_tokens=tokens,
                        total_cost_usd=cost,
                        error=result.get("error"),
                    )
                )

            # Determine overall run status
            total_scenarios = len(scenario_runs)
            if failed > 0:
                overall_status = SimulationStatus.FAILED
            elif completed == total_scenarios:
                overall_status = SimulationStatus.COMPLETED
            else:
                overall_status = SimulationStatus.RUNNING

            # Calculate overall success rate
            success_rates = [sr.success_rate for sr in scenario_runs if sr.success_rate > 0]
            overall_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

            # Use the earliest start_time as the run timestamp
            earliest_time = min(
                (datetime.fromisoformat(r.get("start_time", datetime.now(timezone.utc).isoformat())) for r in results),
                default=datetime.now(timezone.utc),
            )

            runs.append(
                SimulationRunSummary(
                    id=run_id,
                    timestamp=earliest_time,
                    status=overall_status,
                    scenario_runs=scenario_runs,
                    total_scenarios=total_scenarios,
                    completed_scenarios=completed,
                    failed_scenarios=failed,
                    total_tokens=total_tokens,
                    total_cost_usd=total_cost,
                    overall_success_rate=overall_success_rate,
                )
            )

        # Sort runs by timestamp (newest first)
        runs.sort(key=lambda r: r.timestamp, reverse=True)

        total = len(runs)
        paginated = runs[offset : offset + limit]

        return paginated, total

    async def get_run(self, run_id: str) -> SimulationRunDetail | None:  # noqa: PLR0912, PLR0915
        """Get full details for a simulation run.

        Args:
            run_id: Run identifier.

        Returns:
            SimulationRunDetail if found, None otherwise.
        """
        result_files = self.results_dir.glob("result_*.json")

        # Find all results for this run_id
        results = []
        for path in result_files:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("run_id") == run_id:
                    results.append(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse result file {path}: {e}")
                continue

        if not results:
            return None

        # Build full scenario run details
        scenario_runs = []
        total_tokens = 0
        total_cost = 0.0
        completed = 0
        failed = 0

        for result in results:
            metrics = result.get("metrics") or {}
            status = SimulationStatus(result.get("status", "completed"))

            if status == SimulationStatus.COMPLETED:
                completed += 1
            elif status in (SimulationStatus.FAILED, SimulationStatus.TIMEOUT):
                failed += 1

            tokens = metrics.get("total_tokens", 0)
            cost = metrics.get("total_cost_usd", 0.0)
            total_tokens += tokens
            total_cost += cost

            # Parse turns
            turns = []
            for turn in result.get("turns", []):
                token_usage = turn.get("token_usage")
                # Extract only prompt, completion, and total tokens
                if hasattr(token_usage, "model_dump"):
                    token_usage = token_usage.model_dump(include={"prompt_tokens", "completion_tokens", "total_tokens"})
                elif isinstance(token_usage, dict):
                    token_usage = {
                        "prompt_tokens": token_usage.get("prompt_tokens", 0),
                        "completion_tokens": token_usage.get("completion_tokens", 0),
                        "total_tokens": token_usage.get("total_tokens", 0),
                    }
                else:
                    token_usage = None
                checkers = [
                    CheckerResultItemResponse(
                        type=c.get("type", "unknown"),
                        completed=c.get("completed", False),
                        reason=c.get("reason", ""),
                    )
                    for c in turn.get("checkers", [])
                ]
                turns.append(
                    TurnResultResponse(
                        turn_index=turn.get("turn_index", 0),
                        task_index=turn.get("task_index", 0),
                        user_message=turn.get("user_message", ""),
                        assistant_message=turn.get("assistant_message", ""),
                        tool_calls=turn.get("tool_calls", []),
                        task_completed=turn.get("task_completed", False),
                        task_completed_reason=turn.get("task_completed_reason", ""),
                        token_usage=token_usage,
                        latency_ms=turn.get("latency_ms"),
                        checkers=checkers,
                        checker_mode=turn.get("checker_mode", "all"),
                    )
                )

            # Parse tasks
            tasks = []
            for task in result.get("tasks", []):
                tasks.append(
                    TaskResultResponse(
                        task_index=task.get("task_index", 0),
                        description=task.get("description", ""),
                        completed=task.get("completed", False),
                        turns_taken=task.get("turns_taken", 0),
                        final_reason=task.get("final_reason", ""),
                    )
                )

            # Parse response chunks
            response_chunks = []
            for chunk in result.get("response_chunks", []):
                response_chunks.append(
                    ResponseChunkResponse(
                        turn_index=chunk.get("turn_index", 0),
                        task_index=chunk.get("task_index", 0),
                        chunk_index=chunk.get("chunk_index", 0),
                        chunk_type=chunk.get("chunk_type", "unknown"),
                        chunk_data=chunk.get("chunk_data", {}),
                    )
                )

            # Get scenario_run_id, falling back to generated one for old results
            scenario_name = result.get("scenario_name", "Unknown")
            scenario_run_id = result.get("scenario_run_id", self._generate_scenario_run_id(scenario_name))

            scenario_runs.append(
                ScenarioRunDetail(
                    id=scenario_run_id,
                    scenario_name=scenario_name,
                    persona=result.get("persona"),
                    status=status,
                    start_time=datetime.fromisoformat(
                        result.get("start_time", datetime.now(timezone.utc).isoformat())
                    ),
                    end_time=datetime.fromisoformat(result["end_time"]) if result.get("end_time") else None,
                    turns=turns,
                    tasks=tasks,
                    response_chunks=response_chunks,
                    metrics=metrics if metrics else None,
                    error=result.get("error"),
                )
            )

        # Determine overall run status
        total_scenarios = len(scenario_runs)
        if failed > 0:
            overall_status = SimulationStatus.FAILED
        elif completed == total_scenarios:
            overall_status = SimulationStatus.COMPLETED
        else:
            overall_status = SimulationStatus.RUNNING

        # Calculate overall success rate
        success_rates = [sr.metrics.get("success_rate", 0.0) for sr in scenario_runs if sr.metrics]
        overall_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        # Use the earliest start_time as the run timestamp
        earliest_time = min(
            (sr.start_time for sr in scenario_runs),
            default=datetime.now(timezone.utc),
        )

        return SimulationRunDetail(
            id=run_id,
            timestamp=earliest_time,
            status=overall_status,
            scenario_runs=scenario_runs,
            total_scenarios=total_scenarios,
            completed_scenarios=completed,
            failed_scenarios=failed,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            overall_success_rate=overall_success_rate,
        )
