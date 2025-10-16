from collections import defaultdict
from collections.abc import Iterable

from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.hotpot_qa import HotpotQAResult


class HotpotQAExactMatch(Metric[HotpotQAResult]):
    """Computes EM over HotpotQA by type and overall."""

    @staticmethod
    async def compute(results: list[HotpotQAResult]) -> dict:
        """Compute EM. Returns hotpotqa_<type>_em and hotpotqa_overall_em."""
        buckets: dict[str, list[float]] = defaultdict(list)
        for r in results:
            em = r.em_value
            t = r.qtype or "unknown"
            buckets[t].append(em)
            buckets["overall"].append(em)

        def avg(vals: Iterable[float]) -> float:
            lst = list(vals)
            return float(sum(lst) / len(lst)) if lst else 0.0

        metrics: dict[str, float] = {}
        for t, vals in buckets.items():
            metrics[f"hotpotqa_{t}_em"] = avg(vals)
        return metrics


class HotpotQAF1(Metric[HotpotQAResult]):
    """Computes token-level F1 over HotpotQA by type and overall."""

    @staticmethod
    async def compute(results: list[HotpotQAResult]) -> dict:
        """Compute F1. Returns hotpotqa_<type>_f1 and hotpotqa_overall_f1."""
        buckets: dict[str, list[float]] = defaultdict(list)
        for r in results:
            f1v = r.f1_value
            t = r.qtype or "unknown"
            buckets[t].append(f1v)
            buckets["overall"].append(f1v)

        def avg(vals: Iterable[float]) -> float:
            lst = list(vals)
            return float(sum(lst) / len(lst)) if lst else 0.0

        metrics: dict[str, float] = {}
        for t, vals in buckets.items():
            metrics[f"hotpotqa_{t}_f1"] = avg(vals)
        return metrics
