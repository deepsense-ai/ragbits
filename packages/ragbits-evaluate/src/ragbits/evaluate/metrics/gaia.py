from statistics import mean

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.gaia import GaiaResult


class GaiaOutcome(Metric[GaiaResult]):
    """
    Computes task success rate over GAIA tasks.
    Measures the fraction of tasks that were successfully solved.
    """

    @staticmethod
    async def compute(results: list[GaiaResult]) -> dict:
        """Compute task success rate.

        Returns:
            Dictionary with gaia_task_success_rate: fraction of successfully solved tasks.
        """
        success_count = sum(1 for r in results if r.task_success)
        success_rate = (success_count / len(results)) if results else 0.0

        return {"gaia_task_success_rate": float(success_rate)}


class GaiaTooling(Metric[GaiaResult]):
    """
    Tool utilization and performance metrics:
    - gaia_tool_trigger_rate: fraction of tasks where tools were used
    - gaia_avg_num_tool_calls: average number of tool calls per task
    - gaia_avg_tool_error_count: average number of tool errors per task
    - averaged_freq: average tool usage/calls per task
    """

    @staticmethod
    async def compute(results: list[GaiaResult]) -> dict:
        """Compute tool utilization and performance metrics.

        Returns:
            Dictionary with tool trigger rate, average tool calls, average errors,
            and flattened tool frequency usage as numeric metrics.
        """
        tool_triggered_count = sum(1 for r in results if r.tool_triggered)
        tool_trigger_rate = (tool_triggered_count / len(results)) if results else 0.0
        avg_tool_calls = float(mean(r.num_tool_calls for r in results)) if results else 0.0
        avg_tool_errors = float(mean(r.tool_error_count for r in results)) if results else 0.0

        # tool frequency as average per task (mean calls per task per tool)
        total_tasks = len(results) if results else 1
        aggregated_counts: dict[str, int] = {}
        for r in results:
            if r.tool_names:
                for name in r.tool_names:
                    aggregated_counts[name] = aggregated_counts.get(name, 0) + 1
        averaged_freq: dict[str, float] = {
            f"gaia_tool_frequency_usage.{name}": (count / total_tasks) for name, count in aggregated_counts.items()
        }

        return {
            "gaia_tool_trigger_rate": float(tool_trigger_rate),
            "gaia_avg_num_tool_calls": avg_tool_calls,
            "gaia_avg_tool_error_count": avg_tool_errors,
            **averaged_freq,
        }


class GaiaEfficiency(Metric[GaiaResult]):
    """
    Efficiency and resource usage metrics:
    - gaia_avg_latency_ms: average response latency in milliseconds
    """

    @staticmethod
    async def compute(results: list[GaiaResult]) -> dict:
        """Compute efficiency and resource usage metrics.

        Returns:
            Dictionary with average latency.
        """
        avg_latency = float(mean(r.total_latency_ms for r in results)) if results else 0.0

        return {
            "gaia_avg_latency_ms": avg_latency,
        }
