import math
from statistics import mean

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.human_eval import HumanEvalResult


class HumanEvalPassAtK(Metric[HumanEvalResult]):
    """
    Computes pass@k over HumanEval tasks.
    Measures the fraction of tasks with at least one passing sample out of k attempts.
    """

    def __init__(self, k: int = 1) -> None:
        super().__init__()
        self.k = k

    async def compute(self, results: list[HumanEvalResult]) -> dict:
        """Compute pass@k averaged over tasks.

        Returns:
            Dictionary with humaneval_pass@k: fraction of tasks with at least one passing sample.
        """
        values = []
        for r in results:
            n = len(r.passed_mask)
            m = sum(1 for x in r.passed_mask if x)
            k = min(self.k, n)
            if n == 0 or k == 0:
                values.append(0.0)
                continue
            if m == 0:
                values.append(0.0)
                continue
            if m == n:
                values.append(1.0)
                continue
            # 1 - C(n-m, k) / C(n, k)
            denom = math.comb(n, k)
            numer = math.comb(n - m, k) if n - m >= k else 0
            values.append(1.0 - (numer / denom))
        return {f"humaneval_pass@{self.k}": float(mean(values)) if values else 0.0}


class HumanEvalQualityPerf(Metric[HumanEvalResult]):
    """
    Code quality and execution performance metrics:
    - humaneval_compile_rate: fraction of samples that compiled
    - humaneval_syntax_error_rate: fraction of samples with syntax error (compile failed)
    - humaneval_assert_fail_rate: fraction of samples that ran but failed assertions
    - humaneval_runtime_error_rate: fraction of samples with other runtime errors
    - humaneval_timeout_rate: fraction of samples that timed out
    - humaneval_tasks_solved: fraction of tasks with any passing sample
    - humaneval_avg_exec_time_sec: average exec time over compilable runs
    """

    @staticmethod
    async def compute(results: list[HumanEvalResult]) -> dict:
        """Compute code quality and execution performance metrics.

        Returns:
            Dictionary with compile rates, error rates, tasks solved rate, and average execution time.
        """
        total_samples = sum(len(r.passed_mask) for r in results)
        compiled = 0
        syntax_errors = 0
        assert_fails = 0
        runtime_errors = 0
        timeouts = 0
        any_pass = sum(1 for r in results if any(r.passed_mask))
        durations: list[float] = []

        for r in results:
            for ok, err, dur in zip(r.compile_ok_mask, r.errors, r.exec_durations_sec, strict=False):
                if ok:
                    compiled += 1
                    durations.append(dur)
                    if err:
                        if err.startswith("AssertionError"):
                            assert_fails += 1
                        elif err.startswith("TimeoutError"):
                            timeouts += 1
                        else:
                            runtime_errors += 1
                else:
                    # Compile failed: count as syntax error
                    syntax_errors += 1

        compile_rate = (compiled / total_samples) if total_samples else 0.0
        syntax_error_rate = (syntax_errors / total_samples) if total_samples else 0.0
        assert_fail_rate = (assert_fails / total_samples) if total_samples else 0.0
        runtime_error_rate = (runtime_errors / total_samples) if total_samples else 0.0
        timeout_rate = (timeouts / total_samples) if total_samples else 0.0
        tasks_solved = (any_pass / len(results)) if results else 0.0
        avg_exec_time = float(mean(durations)) if durations else 0.0

        return {
            "humaneval_compile_rate": float(compile_rate),
            "humaneval_syntax_error_rate": float(syntax_error_rate),
            "humaneval_assert_fail_rate": float(assert_fail_rate),
            "humaneval_runtime_error_rate": float(runtime_error_rate),
            "humaneval_timeout_rate": float(timeout_rate),
            "humaneval_tasks_solved": float(tasks_solved),
            "humaneval_avg_exec_time_sec": avg_exec_time,
        }
