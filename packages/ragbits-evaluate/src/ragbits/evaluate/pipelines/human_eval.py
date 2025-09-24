import asyncio
import contextlib
import io
import json
import multiprocessing
import textwrap
import time
from collections.abc import Iterable
from dataclasses import dataclass
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from typing_extensions import Self

from ragbits.agents import Agent
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


class HumanEvalData(EvaluationData):
    """
    Represents a single HumanEval task.
    """

    task_id: str
    prompt: str
    entry_point: str
    test: str
    canonical_solution: str | None = None


@dataclass
class HumanEvalResult(EvaluationResult):
    """
    Represents the result of evaluating a single HumanEval task.
    """

    task_id: str
    entry_point: str
    samples: list[str]
    passed_mask: list[bool]
    exec_durations_sec: list[float]
    compile_ok_mask: list[bool]
    errors: list[str | None]


def _execute_in_subprocess(
    source: str, entry_point: str, test_code: str, timeout_sec: int = 10, memory_limit_mb: int | None = 512
) -> tuple[bool, float, str | None]:
    """Run candidate against HumanEval test in a subprocess with timeout."""

    def _runner(pipe: Connection) -> None:
        captured_out = io.StringIO()
        start = time.perf_counter()

        try:
            with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_out):
                # Apply soft resource limits -> NOT A SANDBOX
                with contextlib.suppress(Exception):
                    import os  # type: ignore
                    import resource  # type: ignore
                    import tempfile  # type: ignore

                    cpu_secs = max(1, timeout_sec)
                    resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))

                    if memory_limit_mb is not None:
                        mem_bytes = int(memory_limit_mb) * 1024 * 1024
                        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

                    # Minimal extra security
                    for rlim, val in (
                        (getattr(resource, "RLIMIT_NOFILE", None), 256),
                        (getattr(resource, "RLIMIT_NPROC", None), 64),
                        (getattr(resource, "RLIMIT_FSIZE", None), 10 * 1024 * 1024),
                    ):
                        if rlim is not None:
                            with contextlib.suppress(Exception):
                                resource.setrlimit(rlim, (val, val))

                    # Temporary working directory for solution
                    tmp = tempfile.TemporaryDirectory()
                    with contextlib.suppress(Exception):
                        os.chdir(tmp.name)

                globals_dict: dict[str, Any] = {"__name__": "__main__"}
                exec(compile(source, filename="candidate.py", mode="exec"), globals_dict)  # noqa: S102

                if entry_point not in globals_dict:
                    raise NameError(f"Entry point '{entry_point}' not defined")

                harness = textwrap.dedent(f"candidate = {entry_point}\n").lstrip()
                test_code_clean = textwrap.dedent(test_code).lstrip()
                compiled_test = compile(
                    harness + "\n" + test_code_clean + "\ncheck(candidate)", filename="test.py", mode="exec"
                )
                exec(compiled_test, globals_dict)  # noqa: S102

            duration = time.perf_counter() - start
            pipe.send((True, duration, None))

        except Exception as e:
            duration = time.perf_counter() - start
            pipe.send((False, duration, f"{e.__class__.__name__}: {e}"))

    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=_runner, args=(child_conn,))
    proc.start()
    proc.join(timeout=timeout_sec)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return False, float(timeout_sec), "TimeoutError: execution exceeded time limit"

    passed, duration, err = parent_conn.recv()
    return bool(passed), float(duration), (str(err) if err is not None else None)


class HumanEvalPipeline(
    EvaluationPipeline[Agent[LLMClientOptionsT, None, str] | LLM[LLMClientOptionsT], HumanEvalData, HumanEvalResult]
):
    """HumanEval evaluation pipeline for code generation models/agents."""

    def __init__(
        self,
        evaluation_target: Agent[LLMClientOptionsT, None, str] | LLM[LLMClientOptionsT],
        *,
        n_samples: int = 1,
        timeout_sec: int = 10,
        temperature: float | None = None,
        seed: int | None = None,
        memory_limit_mb: int | None = 512,
        per_example_log_file: Path | None = None,
        extended_logs: bool = False,
    ) -> None:
        super().__init__(evaluation_target=evaluation_target)
        self.n_samples = n_samples
        self.timeout_sec = timeout_sec
        self.temperature = temperature
        self.seed = seed
        self.memory_limit_mb = memory_limit_mb
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
                config["evaluation_target"] = LLM.subclass_from_config(config)
        return super().from_config(config)

    async def __call__(self, data: Iterable[HumanEvalData]) -> Iterable[HumanEvalResult]:
        """Generate code completions per task and evaluate them.
        Returns list of `HumanEvalResult`, one per input task.
        """
        results: list[HumanEvalResult] = []

        for row in data:
            prompt_input = row.prompt
            samples: list[str] = []
            compile_ok: list[bool] = []
            pass_mask: list[bool] = []
            durations: list[float] = []
            errors: list[str | None] = []

            # Produce n samples
            gen_tasks = []
            for _ in range(self.n_samples):
                if self.extended_logs:
                    gen_tasks.append(self._generate_with_debug(prompt_input))
                else:
                    gen_tasks.append(self._generate_code(prompt_input))
            generations = await asyncio.gather(*gen_tasks, return_exceptions=True)

            debug_traces: list[dict | None] | None = [] if self.extended_logs else None

            for _, raw in enumerate(generations):
                if isinstance(raw, Exception):
                    samples.append("")
                    compile_ok.append(False)
                    pass_mask.append(False)
                    durations.append(0.0)
                    err_msg = f"GenerationError: {raw.__class__.__name__}: {raw}"
                    errors.append(err_msg)
                    if self.extended_logs and debug_traces is not None:
                        debug_traces.append({"error": err_msg})
                    continue

                if self.extended_logs:
                    # Raw is (content, debug)
                    content, dbg = raw
                    code = self._sanitize_code(content)
                    samples.append(code)
                    if debug_traces is not None:
                        debug_traces.append(dbg)
                else:
                    # Raw is a simple string
                    code = self._sanitize_code(raw)
                    samples.append(code)

                # Compile check
                try:
                    compile(code, filename="candidate.py", mode="exec")
                    compile_ok.append(True)
                except Exception as e:  # noqa: BLE001
                    compile_ok.append(False)
                    pass_mask.append(False)
                    durations.append(0.0)
                    errors.append(f"SyntaxError: {e}")
                    continue

                ok, dur, err = _execute_in_subprocess(
                    code,
                    row.entry_point,
                    row.test,
                    timeout_sec=self.timeout_sec,
                    memory_limit_mb=self.memory_limit_mb,
                )
                pass_mask.append(ok)
                durations.append(dur)
                errors.append(err)

            result = HumanEvalResult(
                task_id=row.task_id,
                entry_point=row.entry_point,
                samples=samples,
                passed_mask=pass_mask,
                exec_durations_sec=durations,
                compile_ok_mask=compile_ok,
                errors=errors,
            )
            results.append(result)
            ext_log_str = (
                json.dumps(debug_traces, ensure_ascii=False, default=str) if (self.extended_logs and debug_traces is not None) else None
            )
            self._log_example(row, result, ext_log_str)
        return results

    @staticmethod
    def _sanitize_code(text: str) -> str:
        """Basic cleanup for LLM answers.

        - Trim whitespace and normalize newlines
        - If fenced with ```...```, take the first fence block, drop language tag
        """
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if "```" in cleaned:
            start = cleaned.find("```")
            end = cleaned.find("```", start + 3)
            if end != -1:
                inside = cleaned[start + 3 : end].lstrip()
                # drop a possible language tag line
                if "\n" in inside:
                    first, rest = inside.split("\n", 1)
                    cleaned = rest if first.strip().lower().startswith("python") else inside
                else:
                    cleaned = inside
        return cleaned.strip()

    def _init_log_file(self) -> None:
        """Ensure the per-example log file exists if logging is enabled."""
        if self.per_example_log_file is None:
            return
        self.per_example_log_file.parent.mkdir(parents=True, exist_ok=True)
        self.per_example_log_file.touch(exist_ok=True)

    def _log_example(self, row: HumanEvalData, result: HumanEvalResult, extended_log: str | None = None) -> None:
        """Append a single NDJSON record for debugging if enabled."""
        if self.per_example_log_file is None:
            return
        record: dict[str, object] = {
            "task_id": row.task_id,
            "entry_point": row.entry_point,
            "n_samples": len(result.samples),
            "samples": result.samples,
            "compile_ok_mask": result.compile_ok_mask,
            "passed_mask": result.passed_mask,
            "exec_durations_sec": result.exec_durations_sec,
            "errors": result.errors,
        }
        record["extended_debug_logging"] = extended_log or "[]"
        with open(self.per_example_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def _generate_code(self, prompt: str) -> str:
        """Generate final answer code from Agent or raw LLM.

        Sampling/temperature/seed should be configured on the Agent/LLM itself.
        """
        target = self.evaluation_target
        if isinstance(target, Agent):
            res = await target.run(prompt)
            return str(res.content)

        resp = await target.generate(prompt)
        return str(resp)

    async def _generate_with_debug(self, prompt: str) -> tuple[str, dict | None]:
        """Generate code and capture tool/history/usage for logging (as raw content)."""
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
