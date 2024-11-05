import time
from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from tqdm.asyncio import tqdm

from ragbits.evaluate.loaders.base import DataLoader
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines.base import EvaluationPipeline, EvaluationResult


class Evaluator:
    """
    Evaluator class.
    """

    async def compute(
        self,
        pipeline: EvaluationPipeline,
        dataloader: DataLoader,
        metrics: MetricSet,
    ) -> dict[str, Any]:
        """
        Compute the evaluation results for the given pipeline and data.

        Args:
            pipeline: The pipeline to be evaluated.
            dataloader: The dataloader to load the data.
            metrics: The metrics to be computed.

        Returns:
            The evaluation results.
        """
        dataset = await dataloader.load()
        results, perf_results = await self._call_pipeline(pipeline, dataset)
        computed_metrics = self._compute_metrics(metrics, results)
        processed_results = self._results_processor(results)

        return {
            **perf_results,
            **computed_metrics,
            **processed_results,
        }

    async def _call_pipeline(
        self,
        pipeline: EvaluationPipeline,
        dataset: Iterable,
    ) -> tuple[list[EvaluationResult], dict[str, Any]]:
        """
        Call the pipeline with the given data.

        Args:
            pipeline: The pipeline to be called.
            dataset: The dataset to be processed.

        Returns:
            The evaluation results and performance metrics.
        """
        start_time = time.perf_counter()
        pipe_outputs = await tqdm.gather(*[pipeline(data) for data in dataset], desc="Evaluation")
        end_time = time.perf_counter()
        return pipe_outputs, self._compute_time_perf(start_time, end_time, len(pipe_outputs))

    @staticmethod
    def _results_processor(results: list[EvaluationResult]) -> dict[str, Any]:
        """
        Process the results.

        Args:
            results: The evaluation results.

        Returns:
            The processed results.
        """
        return {"results": [asdict(result) for result in results]}

    @staticmethod
    def _compute_metrics(metrics: MetricSet, results: list[EvaluationResult]) -> dict[str, Any]:
        """
        Compute a metric using the given inputs.

        Args:
            metrics: The metrics to be computed.
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        return {"metrics": metrics.compute(results)}

    @staticmethod
    def _compute_time_perf(start_time: float, end_time: float, num_samples: int) -> dict[str, Any]:
        """
        Compute the performance metrics.

        Args:
            start_time: The start time.
            end_time: The end time.
            num_samples: The number of samples.

        Returns:
            The performance metrics.
        """
        latency = end_time - start_time
        throughput = num_samples / latency
        latency_sample = 1.0 / throughput if throughput > 0 else 0.0

        return {
            "time_perf": {
                "total_time_in_seconds": latency,
                "samples_per_second": throughput,
                "latency_in_seconds": latency_sample,
            },
        }
