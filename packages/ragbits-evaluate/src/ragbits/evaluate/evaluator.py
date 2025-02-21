import asyncio
import time
from collections.abc import Iterable
from dataclasses import asdict

from pydantic import BaseModel
from tqdm.asyncio import tqdm

from ragbits.core.utils.config_handling import ObjectContructionConfig, WithConstructionConfig
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines.base import EvaluationPipeline, EvaluationResult


class EvaluatorConfig(BaseModel):
    """
    Schema for for the dict taken by `Evaluator.run_from_config` method.
    """

    dataloader: ObjectContructionConfig
    pipeline: ObjectContructionConfig
    metrics: dict[str, ObjectContructionConfig]


class Evaluator(WithConstructionConfig):
    """
    Evaluator class.
    """

    CONCURRENCY: int = 10

    @classmethod
    async def run_from_config(cls, config: dict) -> dict:
        """
        Runs the evaluation based on configuration.

        Args:
            config: Evaluation config.

        Returns:
            The evaluation results.
        """
        model = EvaluatorConfig.model_validate(config)
        dataloader: DataLoader = DataLoader.subclass_from_config(model.dataloader)
        pipeline: EvaluationPipeline = EvaluationPipeline.subclass_from_config(model.pipeline)
        metrics: MetricSet = MetricSet.from_config(model.metrics)

        return await cls().compute(
            pipeline=pipeline,
            dataloader=dataloader,
            metrics=metrics,
        )

    async def compute(
        self,
        pipeline: EvaluationPipeline,
        dataloader: DataLoader,
        metrics: MetricSet,
    ) -> dict:
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
        await pipeline.prepare()

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
        dataset: Iterable[dict],
    ) -> tuple[list[EvaluationResult], dict]:
        """
        Call the pipeline with the given data.

        Args:
            pipeline: The pipeline to be called.
            dataset: The dataset to be processed.

        Returns:
            The evaluation results and performance metrics.
        """
        semaphore = asyncio.Semaphore(self.CONCURRENCY)

        async def _call_pipeline_with_semaphore(data: dict) -> EvaluationResult:
            async with semaphore:
                return await pipeline(data)

        start_time = time.perf_counter()
        pipe_outputs = await tqdm.gather(*[_call_pipeline_with_semaphore(data) for data in dataset], desc="Evaluation")
        end_time = time.perf_counter()

        return pipe_outputs, self._compute_time_perf(start_time, end_time, len(pipe_outputs))

    @staticmethod
    def _results_processor(results: list[EvaluationResult]) -> dict:
        """
        Process the results.

        Args:
            results: The evaluation results.

        Returns:
            The processed results.
        """
        return {"results": [asdict(result) for result in results]}

    @staticmethod
    def _compute_metrics(metrics: MetricSet, results: list[EvaluationResult]) -> dict:
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
    def _compute_time_perf(start_time: float, end_time: float, num_samples: int) -> dict:
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
