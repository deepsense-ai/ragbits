import json
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typing_extensions import Self

from ragbits.agents import Agent
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata, Usage
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


class MoreHopQAData(EvaluationData):
    """
    Represents a single MoreHopQA task.
    """

    task_id: str
    question: str
    answer: str


@dataclass
class MoreHopQAResult(EvaluationResult):
    """
    Represents the result of evaluating a single MoreHopQA task.
    """

    task_id: str
    question: str
    answer: str
    predicted_result: str
    task_success: bool
    tool_triggered: bool
    num_tool_calls: int
    tool_error_count: int
    total_latency_ms: int
    usage: Usage | None = None
    tool_names: list[str] | None = None


class MoreHopQAPipeline(
    EvaluationPipeline[Agent[LLMClientOptionsT, None, str] | LLM[LLMClientOptionsT], MoreHopQAData, MoreHopQAResult]
):
    """MoreHopQA evaluation pipeline for multi-hop question answering models/agents."""

    def __init__(
        self,
        evaluation_target: Agent[LLMClientOptionsT, None, str] | LLM[LLMClientOptionsT],
        *,
        system_prompt: str | None = None,
        per_example_log_file: Path | None = None,
        extended_logs: bool = False,
    ) -> None:
        super().__init__(evaluation_target=evaluation_target)
        self.system_prompt = system_prompt
        self.per_example_log_file = per_example_log_file
        self.extended_logs = extended_logs
        self._init_log_file()

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """Create pipeline from config.
        Attempts Agent first, falls back to raw LLM construction.
        """
        if "evaluation_target" not in config:
            try:
                config["evaluation_target"] = Agent.from_config(config)
            except Exception:
                config["evaluation_target"] = LLM.from_config(config)
        return super().from_config(config)

    @staticmethod
    def _count_tool_errors(tool_calls: list) -> int:
        """Count tool errors from tool_calls."""
        tool_error_count = 0
        for call in tool_calls:
            try:
                if isinstance(call.result, dict) and "error" in call.result:
                    tool_error_count += 1
            except Exception as exc:
                logging.getLogger(__name__).debug("Error while parsing tool call result: %s", exc)
        return tool_error_count

    @staticmethod
    def _extract_tool_names(tool_calls: list) -> list[str] | None:
        """Extract tool names from tool_calls."""
        if not tool_calls:
            return None
        tool_names = []
        for call in tool_calls:
            try:
                name = getattr(call, "name", None)
                if name is None and isinstance(call, dict):
                    name = call.get("name")
                if name:
                    tool_names.append(str(name))
            except Exception as exc:
                logging.getLogger(__name__).debug("Tool name extraction error: %s", exc)
        return tool_names

    async def __call__(self, data: Iterable[MoreHopQAData]) -> Iterable[MoreHopQAResult]:
        """Generate answer completions per task and evaluate them.
        Returns list of `MoreHopQAResult`, one per input task.
        """
        results: list[MoreHopQAResult] = []

        for row in data:
            start_time = time.perf_counter()

            prompt_input = row.question
            debug_traces: list[dict | None] | None = [] if self.extended_logs else None

            usage: Usage | None = None
            try:
                if self.extended_logs:
                    content, dbg = await self._generate_with_debug(prompt_input)
                    if debug_traces is not None:
                        debug_traces.append(dbg)
                    tool_calls = cast(list, (dbg or {}).get("tool_calls") or [])
                    usage = (dbg or {}).get("usage")
                else:
                    content, usage, tool_calls = await self._generate_answer(prompt_input)

            except Exception as generation_exc:
                content = ""
                tool_calls = []
                usage = None
                err_msg = f"GenerationError: {generation_exc.__class__.__name__}: {generation_exc}"
                if self.extended_logs and debug_traces is not None:
                    debug_traces.append({"error": err_msg})

            end_time = time.perf_counter()

            # Compute metrics
            predicted = str(content).strip()

            # Check if the answer is in the predicted result (normalized)
            task_success = self._normalize(row.answer) in self._normalize(predicted)

            tool_triggered = bool(tool_calls)
            num_tool_calls = len(tool_calls)
            tool_error_count = MoreHopQAPipeline._count_tool_errors(tool_calls)
            tool_names = MoreHopQAPipeline._extract_tool_names(tool_calls)
            total_latency_ms = int((end_time - start_time) * 1000)

            result = MoreHopQAResult(
                task_id=row.task_id,
                question=row.question,
                answer=row.answer,
                predicted_result=content,
                task_success=task_success,
                tool_triggered=tool_triggered,
                num_tool_calls=num_tool_calls,
                tool_error_count=tool_error_count,
                total_latency_ms=total_latency_ms,
                usage=usage,
                tool_names=tool_names,
            )
            results.append(result)
            ext_log_str = (
                json.dumps(debug_traces, ensure_ascii=False, default=str)
                if (self.extended_logs and debug_traces is not None)
                else None
            )
            self._log_example(row, result, ext_log_str)

        return results

    def _init_log_file(self) -> None:
        """Ensure the per-example log file exists if logging is enabled."""
        if self.per_example_log_file is None:
            return
        self.per_example_log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.per_example_log_file, "w", encoding="utf-8") as _:
            pass

    def _log_example(self, row: MoreHopQAData, result: MoreHopQAResult, extended_log: str | None = None) -> None:
        """Append a single NDJSON record for debugging if enabled."""
        if self.per_example_log_file is None:
            return
        # per-task tool frequency map from tool names
        tool_frequency_usage: dict[str, int] = {}
        if result.tool_names:
            for name in result.tool_names:
                tool_frequency_usage[name] = tool_frequency_usage.get(name, 0) + 1
        record: dict[str, object] = {
            "task_id": row.task_id,
            "question": row.question,
            "answer": row.answer,
            "predicted": str(result.predicted_result),
            "task_success": result.task_success,
            "tool_triggered": result.tool_triggered,
            "num_tool_calls": result.num_tool_calls,
            "tool_error_count": result.tool_error_count,
            "total_latency_ms": result.total_latency_ms,
            "tool_frequency_usage": tool_frequency_usage,
        }
        record["extended_debug_logging"] = extended_log or "[]"
        with open(self.per_example_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def _generate_answer(self, prompt: str) -> tuple[str, Usage, list]:
        """Generate final answer from Agent or raw LLM and capture usage and tool calls."""
        target = self.evaluation_target
        if isinstance(target, Agent):
            res = await target.run(prompt)
            return str(res.content), res.usage, (res.tool_calls or [])

        resp = cast(LLMResponseWithMetadata[str], await target.generate_with_metadata(prompt))
        return str(resp.content), (resp.usage or Usage()), []

    async def _generate_with_debug(self, prompt: str) -> tuple[str, dict | None]:
        """Generate answer and capture tool/history/usage for logging (as raw content)."""
        target = self.evaluation_target
        if isinstance(target, Agent):
            res = await target.run(prompt)
            dbg = {
                "history": res.history,
                "tool_calls": res.tool_calls,
                "usage": res.usage,
                "metadata": res.metadata,
            }
            return str(res.content), dbg
        resp = await target.generate(prompt)
        return str(resp), None

    @staticmethod
    def _normalize(text: str) -> str:
        """Basic normalization for answer equality checks: lowercase, strip spaces."""
        return "".join(ch.lower() for ch in text.strip() if not ch.isspace())
