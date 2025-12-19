"""Key-value based evaluation report storage using core KVStore."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ragbits.evaluate.agent_simulation.results import (
    ConversationMetrics,
    ResponseChunk,
    SimulationResult,
    SimulationStatus,
    TaskResult,
    TurnResult,
)
from ragbits.evaluate.api_types import (
    ResultSummary,
    SimulationRunDetail,
    SimulationRunSummary,
)
from ragbits.evaluate.stores.base import EvalReportStore

if TYPE_CHECKING:
    from ragbits.core.storage.kv_store.base import KVStore

logger = logging.getLogger(__name__)


class KVEvalReportStore(EvalReportStore):
    """Key-value based storage for evaluation reports.

    Uses ragbits.core.storage.kv_store for simple JSON storage.
    Stores results, runs, and indexes as JSON documents.

    Example:
        ```python
        from ragbits.core.storage.connections import PostgresConnection
        from ragbits.core.storage.kv_store import PostgresKVStore
        from ragbits.evaluate.stores import KVEvalReportStore

        conn = PostgresConnection(host="localhost", database="mydb")
        kv = PostgresKVStore(connection=conn, table_name="eval_store")
        store = KVEvalReportStore(kv_store=kv)
        ```
    """

    # Key prefixes for different data types
    _RESULT_PREFIX = "result:"
    _RUN_PREFIX = "run:"
    _INDEX_KEY = "index:results"
    _RUNS_INDEX_KEY = "index:runs"

    def __init__(self, kv_store: KVStore[dict[str, Any]]) -> None:
        """Initialize the KV store.

        Args:
            kv_store: KVStore instance from ragbits.core.storage.
        """
        self._kv = kv_store

    async def save_result(
        self,
        run_id: str,
        scenario_run_id: str,
        scenario_name: str,
        result: SimulationResult,
        buffered_chunks: list[ResponseChunk] | None = None,
    ) -> str:
        """Save a simulation result."""
        # Generate result_id
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario_name)
        result_id = f"result_{timestamp}_{safe_name}"

        # Add buffered chunks
        all_chunks = list(result.response_chunks)
        if buffered_chunks:
            chunk_index = len(all_chunks)
            for chunk in buffered_chunks:
                if chunk.chunk_type == "text":
                    continue
                all_chunks.append(
                    ResponseChunk(
                        turn_index=chunk.turn_index,
                        task_index=chunk.task_index,
                        chunk_index=chunk_index,
                        chunk_type=chunk.chunk_type,
                        chunk_data=chunk.chunk_data,
                    )
                )
                chunk_index += 1

        # Serialize result to dict
        result_data = {
            "result_id": result_id,
            "run_id": run_id,
            "scenario_run_id": scenario_run_id,
            "scenario_name": scenario_name,
            "persona": result.persona,
            "status": result.status.value,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "agent_model": result.agent_model,
            "simulated_user_model": result.simulated_user_model,
            "checker_model": result.checker_model,
            "conversation_id": result.conversation_id,
            "final_state": result.final_state,
            "metrics": result.metrics.metrics if result.metrics else None,
            "traces": result.traces,
            "error": result.error,
            "turns": [self._serialize_turn(t) for t in result.turns],
            "tasks": [self._serialize_task(t) for t in result.tasks],
            "response_chunks": [self._serialize_chunk(c) for c in all_chunks],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save result
        await self._kv.set(f"{self._RESULT_PREFIX}{result_id}", result_data)

        # Update results index
        await self._add_to_index(self._INDEX_KEY, result_id, result_data)

        # Update or create run
        await self._update_run(run_id, result_id, result_data)

        logger.info(f"Saved result {result_id} to KV store")
        return result_id

    def _serialize_turn(self, turn: TurnResult) -> dict[str, Any]:  # noqa: PLR6301
        """Serialize a turn result."""
        token_usage = None
        if turn.token_usage:
            if hasattr(turn.token_usage, "model_dump"):
                token_usage = turn.token_usage.model_dump()
            elif isinstance(turn.token_usage, dict):
                token_usage = turn.token_usage

        return {
            "turn_index": turn.turn_index,
            "task_index": turn.task_index,
            "user_message": turn.user_message,
            "assistant_message": turn.assistant_message,
            "tool_calls": turn.tool_calls,
            "task_completed": turn.task_completed,
            "task_completed_reason": turn.task_completed_reason,
            "token_usage": token_usage,
            "latency_ms": turn.latency_ms,
            "checkers": [c.to_dict() for c in turn.checkers] if turn.checkers else [],
            "checker_mode": turn.checker_mode,
        }

    def _serialize_task(self, task: TaskResult) -> dict[str, Any]:  # noqa: PLR6301
        """Serialize a task result."""
        return {
            "task_index": task.task_index,
            "description": task.description,
            "completed": task.completed,
            "turns_taken": task.turns_taken,
            "final_reason": task.final_reason,
            "checkers": task.checkers,
            "checker_mode": task.checker_mode,
        }

    def _serialize_chunk(self, chunk: ResponseChunk) -> dict[str, Any]:  # noqa: PLR6301
        """Serialize a response chunk."""
        return {
            "turn_index": chunk.turn_index,
            "task_index": chunk.task_index,
            "chunk_index": chunk.chunk_index,
            "chunk_type": chunk.chunk_type,
            "chunk_data": chunk.chunk_data,
        }

    async def _add_to_index(self, index_key: str, item_id: str, data: dict[str, Any]) -> None:
        """Add item to an index."""
        index = await self._kv.get(index_key) or {"items": []}

        # Add summary to index
        summary = {
            "id": item_id,
            "scenario_name": data.get("scenario_name"),
            "status": data.get("status"),
            "start_time": data.get("start_time"),
            "created_at": data.get("created_at"),
            "metrics": data.get("metrics"),
        }
        index["items"].insert(0, summary)  # Most recent first

        await self._kv.set(index_key, index)

    async def _update_run(self, run_id: str, result_id: str, result_data: dict[str, Any]) -> None:
        """Update or create a run record."""
        run_key = f"{self._RUN_PREFIX}{run_id}"
        run = await self._kv.get(run_key)

        if run is None:
            run = {
                "id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "running",
                "results": [],
                "total_scenarios": 0,
                "completed_scenarios": 0,
                "failed_scenarios": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }
            # Add to runs index
            runs_index = await self._kv.get(self._RUNS_INDEX_KEY) or {"items": []}
            runs_index["items"].insert(0, {"id": run_id, "timestamp": run["timestamp"]})
            await self._kv.set(self._RUNS_INDEX_KEY, runs_index)

        # Add result to run
        run["results"].append(
            {
                "result_id": result_id,
                "scenario_name": result_data.get("scenario_name"),
                "persona": result_data.get("persona"),
                "status": result_data.get("status"),
                "metrics": result_data.get("metrics"),
            }
        )

        # Update stats
        run["total_scenarios"] = len(run["results"])
        run["completed_scenarios"] = sum(1 for r in run["results"] if r["status"] == "completed")
        run["failed_scenarios"] = sum(1 for r in run["results"] if r["status"] in ("failed", "timeout"))

        metrics = result_data.get("metrics") or {}
        run["total_tokens"] += metrics.get("total_tokens", 0)
        run["total_cost_usd"] += metrics.get("total_cost_usd", 0.0)

        # Update run status
        if run["completed_scenarios"] == run["total_scenarios"]:
            run["status"] = "completed"
        elif run["failed_scenarios"] > 0:
            run["status"] = "failed"

        await self._kv.set(run_key, run)

    async def load_result(self, result_id: str) -> SimulationResult | None:
        """Load a simulation result."""
        data = await self._kv.get(f"{self._RESULT_PREFIX}{result_id}")
        if not data:
            return None

        return self._deserialize_result(data)

    def _deserialize_result(self, data: dict[str, Any]) -> SimulationResult:  # noqa: PLR6301
        """Deserialize a result from dict."""
        from ragbits.evaluate.agent_simulation.results import CheckerResultItem

        turns = []
        for t in data.get("turns", []):
            checkers = [CheckerResultItem.from_dict(c) for c in t.get("checkers", [])]
            turns.append(
                TurnResult(
                    turn_index=t["turn_index"],
                    task_index=t["task_index"],
                    user_message=t.get("user_message", ""),
                    assistant_message=t.get("assistant_message", ""),
                    tool_calls=t.get("tool_calls", []),
                    task_completed=t.get("task_completed", False),
                    task_completed_reason=t.get("task_completed_reason", ""),
                    token_usage=t.get("token_usage"),
                    latency_ms=t.get("latency_ms"),
                    checkers=checkers,
                    checker_mode=t.get("checker_mode", "all"),
                )
            )

        tasks = [
            TaskResult(
                task_index=t["task_index"],
                description=t.get("description", ""),
                completed=t.get("completed", False),
                turns_taken=t.get("turns_taken", 0),
                final_reason=t.get("final_reason", ""),
                checkers=t.get("checkers", []),
                checker_mode=t.get("checker_mode", "all"),
            )
            for t in data.get("tasks", [])
        ]

        chunks = [
            ResponseChunk(
                turn_index=c["turn_index"],
                task_index=c["task_index"],
                chunk_index=c["chunk_index"],
                chunk_type=c["chunk_type"],
                chunk_data=c.get("chunk_data", {}),
            )
            for c in data.get("response_chunks", [])
        ]

        return SimulationResult(
            scenario_name=data["scenario_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            status=SimulationStatus(data["status"]),
            agent_model=data.get("agent_model"),
            simulated_user_model=data.get("simulated_user_model"),
            checker_model=data.get("checker_model"),
            persona=data.get("persona"),
            error=data.get("error"),
            conversation_id=data.get("conversation_id"),
            final_state=data.get("final_state", {}),
            turns=turns,
            tasks=tasks,
            metrics=ConversationMetrics(metrics=data["metrics"]) if data.get("metrics") else None,
            response_chunks=chunks,
            traces=data.get("traces", []),
        )

    async def delete_result(self, result_id: str) -> bool:
        """Delete a simulation result."""
        data = await self._kv.get(f"{self._RESULT_PREFIX}{result_id}")
        if not data:
            return False

        # Remove from result
        await self._kv.delete(f"{self._RESULT_PREFIX}{result_id}")

        # Update index
        index = await self._kv.get(self._INDEX_KEY) or {"items": []}
        index["items"] = [i for i in index["items"] if i["id"] != result_id]
        await self._kv.set(self._INDEX_KEY, index)

        # Update run
        run_id = data.get("run_id")
        if run_id:
            run = await self._kv.get(f"{self._RUN_PREFIX}{run_id}")
            if run:
                run["results"] = [r for r in run["results"] if r["result_id"] != result_id]
                if not run["results"]:
                    await self._kv.delete(f"{self._RUN_PREFIX}{run_id}")
                    # Remove from runs index
                    runs_index = await self._kv.get(self._RUNS_INDEX_KEY) or {"items": []}
                    runs_index["items"] = [i for i in runs_index["items"] if i["id"] != run_id]
                    await self._kv.set(self._RUNS_INDEX_KEY, runs_index)
                else:
                    await self._kv.set(f"{self._RUN_PREFIX}{run_id}", run)

        return True

    async def list_results(self, limit: int = 50, offset: int = 0) -> tuple[list[ResultSummary], int]:
        """List evaluation results with pagination."""
        index = await self._kv.get(self._INDEX_KEY) or {"items": []}
        items = index["items"]
        total = len(items)

        summaries = []
        for item in items[offset : offset + limit]:
            metrics = item.get("metrics") or {}
            summaries.append(
                ResultSummary(
                    result_id=item["id"],
                    scenario_name=item.get("scenario_name", ""),
                    timestamp=datetime.fromisoformat(item["start_time"])
                    if item.get("start_time")
                    else datetime.now(timezone.utc),
                    status=SimulationStatus(item.get("status", "unknown")),
                    tasks_completed=metrics.get("tasks_completed", 0),
                    total_tasks=metrics.get("total_tasks", 0),
                    success_rate=metrics.get("success_rate", 0.0),
                    total_turns=metrics.get("total_turns", 0),
                    total_tokens=metrics.get("total_tokens", 0),
                    total_cost_usd=metrics.get("total_cost_usd", 0.0),
                )
            )

        return summaries, total

    async def list_runs(self, limit: int = 50, offset: int = 0) -> tuple[list[SimulationRunSummary], int]:
        """List simulation runs."""
        runs_index = await self._kv.get(self._RUNS_INDEX_KEY) or {"items": []}
        items = runs_index["items"]
        total = len(items)

        runs = []
        for item in items[offset : offset + limit]:
            run = await self._kv.get(f"{self._RUN_PREFIX}{item['id']}")
            if run:
                runs.append(self._run_to_summary(run))

        return runs, total

    def _run_to_summary(self, run: dict[str, Any]) -> SimulationRunSummary:  # noqa: PLR6301
        """Convert run data to summary."""
        from ragbits.evaluate.api_types import ScenarioRunSummary

        scenario_runs = []
        for r in run.get("results", []):
            metrics = r.get("metrics") or {}
            scenario_runs.append(
                ScenarioRunSummary(
                    id=r["result_id"],
                    scenario_name=r.get("scenario_name", ""),
                    persona=r.get("persona"),
                    status=SimulationStatus(r.get("status", "unknown")),
                    start_time=datetime.now(timezone.utc),  # Not stored in summary
                    end_time=None,
                    total_turns=metrics.get("total_turns", 0),
                    total_tasks=metrics.get("total_tasks", 0),
                    tasks_completed=metrics.get("tasks_completed", 0),
                    success_rate=metrics.get("success_rate", 0.0),
                    total_tokens=metrics.get("total_tokens", 0),
                    total_cost_usd=metrics.get("total_cost_usd", 0.0),
                    error=None,
                )
            )

        success_rates = [sr.success_rate for sr in scenario_runs if sr.success_rate > 0]
        overall_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        return SimulationRunSummary(
            id=run["id"],
            timestamp=datetime.fromisoformat(run["timestamp"]),
            status=SimulationStatus(run.get("status", "unknown")),
            scenario_runs=scenario_runs,
            total_scenarios=run.get("total_scenarios", 0),
            completed_scenarios=run.get("completed_scenarios", 0),
            failed_scenarios=run.get("failed_scenarios", 0),
            total_tokens=run.get("total_tokens", 0),
            total_cost_usd=run.get("total_cost_usd", 0.0),
            overall_success_rate=overall_success_rate,
        )

    async def get_run(self, run_id: str) -> SimulationRunDetail | None:
        """Get full details for a simulation run."""
        run = await self._kv.get(f"{self._RUN_PREFIX}{run_id}")
        if not run:
            return None

        scenario_runs = []
        for r in run.get("results", []):
            # Load full result
            result_data = await self._kv.get(f"{self._RESULT_PREFIX}{r['result_id']}")
            if result_data:
                scenario_runs.append(self._result_to_scenario_detail(result_data))

        success_rates = [sr.metrics.get("success_rate", 0.0) for sr in scenario_runs if sr.metrics]
        overall_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        return SimulationRunDetail(
            id=run["id"],
            timestamp=datetime.fromisoformat(run["timestamp"]),
            status=SimulationStatus(run.get("status", "unknown")),
            scenario_runs=scenario_runs,
            total_scenarios=run.get("total_scenarios", 0),
            completed_scenarios=run.get("completed_scenarios", 0),
            failed_scenarios=run.get("failed_scenarios", 0),
            total_tokens=run.get("total_tokens", 0),
            total_cost_usd=run.get("total_cost_usd", 0.0),
            overall_success_rate=overall_success_rate,
        )

    def _result_to_scenario_detail(self, data: dict[str, Any]) -> Any:  # noqa: PLR6301, ANN401
        """Convert result data to scenario detail."""
        from ragbits.evaluate.api_types import (
            CheckerResultItemResponse,
            ResponseChunkResponse,
            ScenarioRunDetail,
            TaskResultResponse,
            TurnResultResponse,
        )

        turns = []
        for t in data.get("turns", []):
            token_usage = t.get("token_usage")
            if token_usage:
                token_usage = {
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                }
            turns.append(
                TurnResultResponse(
                    turn_index=t["turn_index"],
                    task_index=t["task_index"],
                    user_message=t.get("user_message", ""),
                    assistant_message=t.get("assistant_message", ""),
                    tool_calls=t.get("tool_calls", []),
                    task_completed=t.get("task_completed", False),
                    task_completed_reason=t.get("task_completed_reason", ""),
                    token_usage=token_usage,
                    latency_ms=t.get("latency_ms"),
                    checkers=[
                        CheckerResultItemResponse(
                            type=c.get("type", "unknown"),
                            completed=c.get("completed", False),
                            reason=c.get("reason", ""),
                        )
                        for c in t.get("checkers", [])
                    ],
                    checker_mode=t.get("checker_mode", "all"),
                )
            )

        tasks = [
            TaskResultResponse(
                task_index=t["task_index"],
                description=t.get("description", ""),
                completed=t.get("completed", False),
                turns_taken=t.get("turns_taken", 0),
                final_reason=t.get("final_reason", ""),
            )
            for t in data.get("tasks", [])
        ]

        chunks = [
            ResponseChunkResponse(
                turn_index=c["turn_index"],
                task_index=c["task_index"],
                chunk_index=c["chunk_index"],
                chunk_type=c["chunk_type"],
                chunk_data=c.get("chunk_data", {}),
            )
            for c in data.get("response_chunks", [])
        ]

        return ScenarioRunDetail(
            id=data.get("scenario_run_id", data["result_id"]),
            scenario_name=data["scenario_name"],
            persona=data.get("persona"),
            status=SimulationStatus(data["status"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            turns=turns,
            tasks=tasks,
            response_chunks=chunks,
            metrics=data.get("metrics"),
            error=data.get("error"),
        )
