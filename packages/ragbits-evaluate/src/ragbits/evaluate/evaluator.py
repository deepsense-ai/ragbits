import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Generic, ParamSpec, TypeVar

from pydantic import BaseModel
from tqdm import tqdm

from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.core.utils.helpers import batched
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines.base import EvaluationDataT, EvaluationPipeline, EvaluationResultT, EvaluationTargetT

_CallP = ParamSpec("_CallP")
_CallReturnT = TypeVar("_CallReturnT")


@dataclass
class EvaluationTimePerf:
    """
    Container for evaluation time performance metrics.
    """

    total_time_in_seconds: float
    samples_per_second: float
    latency_in_seconds: float


@dataclass
class EvaluatorResult(Generic[EvaluationResultT]):
    """
    Container for evaluation results.
    """

    metrics: dict[str, int | float]
    results: list[EvaluationResultT]
    errors: list[Exception]
    time_perf: EvaluationTimePerf


class EvaluationConfig(BaseModel):
    """
    Schema for the evaluation run config.
    """

    pipeline: ObjectConstructionConfig
    dataloader: ObjectConstructionConfig
    metrics: dict[str, ObjectConstructionConfig]


class EvaluatorConfig(BaseModel):
    """
    Schema for the evaluator config.
    """

    evaluation: EvaluationConfig
    evaluator: dict | None = None


class Evaluator(WithConstructionConfig):
    """
    Evaluator class.
    """

    def __init__(
        self,
        batch_size: int = 10,
        num_retries: int = 3,
        backoff_multiplier: int = 1,
        backoff_max: int = 60,
    ) -> None:
        """
        Initialize the Evaluator instance.

        Args:
            batch_size: batch size for the evaluation pipeline inference.
            num_retries: The number of retries per evaluation pipeline inference error.
            backoff_multiplier: The base delay multiplier for exponential backoff (in seconds).
            backoff_max: The maximum allowed delay (in seconds) between retries.
        """
        self.batch_size = batch_size
        self.num_retries = num_retries
        self.backoff_multiplier = backoff_multiplier
        self.backoff_max = backoff_max

    @classmethod
    async def run_from_config(cls, config: dict) -> EvaluatorResult:
        """
        Run the evaluation based on configuration.

        Args:
            config: Evaluation config.

        Returns:
            The evaluation results.
        """
        evaluator_config = EvaluatorConfig.model_validate(config)
        evaluation_config = EvaluationConfig.model_validate(evaluator_config.evaluation)
        pipeline: EvaluationPipeline = EvaluationPipeline.subclass_from_config(evaluation_config.pipeline)
        dataloader: DataLoader = DataLoader.subclass_from_config(evaluation_config.dataloader)
        metricset: MetricSet = MetricSet.from_config(evaluation_config.metrics)

        evaluator = cls.from_config(evaluator_config.evaluator or {})
        return await evaluator.compute(
            pipeline=pipeline,
            dataloader=dataloader,
            metricset=metricset,
        )

    async def compute(
        self,
        pipeline: EvaluationPipeline[EvaluationTargetT, EvaluationDataT, EvaluationResultT],
        dataloader: DataLoader[EvaluationDataT],
        metricset: MetricSet[EvaluationResultT],
    ) -> EvaluatorResult[EvaluationResultT]:
        """
        Compute the evaluation results for the given pipeline and data.

        Args:
            pipeline: The pipeline to be evaluated.
            dataloader: The dataloader to load the data.
            metricset: The metrics to be computed.

        Returns:
            The evaluation results.
        """
        await pipeline.prepare()

        dataset = await dataloader.load()
        results, errors, time_perf = await self._call_pipeline(pipeline, dataset)
        metrics = await metricset.compute(results)

        return EvaluatorResult(
            metrics=metrics,
            results=results,
            errors=errors,
            time_perf=time_perf,
        )

    async def _call_pipeline(
        self,
        pipeline: EvaluationPipeline[EvaluationTargetT, EvaluationDataT, EvaluationResultT],
        dataset: Iterable[EvaluationDataT],
    ) -> tuple[list[EvaluationResultT], list[Exception], EvaluationTimePerf]:
        """
        Call the pipeline with the given data.

        Args:
            pipeline: The pipeline to be called.
            dataset: The dataset to be processed.

        Returns:
            The evaluation results and performance metrics.
        """
        start_time = time.perf_counter()
        outputs = [
            await self._call_with_error_handling(pipeline, data)
            for data in tqdm(batched(dataset, self.batch_size), desc="Evaluation")
        ]
        end_time = time.perf_counter()

        errors = [output for output in outputs if isinstance(output, Exception)]
        results = [item for output in outputs if not isinstance(output, Exception) for item in output]

        return results, errors, self._compute_time_perf(start_time, end_time, len(outputs))

    async def _call_with_error_handling(
        self,
        executable: Callable[_CallP, Awaitable[_CallReturnT]],
        *executable_args: _CallP.args,
        **executable_kwargs: _CallP.kwargs,
    ) -> _CallReturnT | Exception:
        """
        Call executable with a standarized error handling.
        If an error occurs, the executable is retried `num_retries` times using randomized exponential backoff.

        Args:
            executable: The callable function to execute.
            executable_args: Positional arguments to pass to the executable.
            executable_kwargs: Keyword arguments to pass to the executable.

        Returns:
            The result of the executable if successful.

        Raises:
            Exception: The last encountered exception after all retries are exhausted.
        """
        for i in range(max(0, self.num_retries) + 1):
            try:
                return await executable(*executable_args, **executable_kwargs)
            except Exception as exc:
                if i == self.num_retries:
                    return exc

                delay = random.uniform(0, min(2**i * self.backoff_multiplier, self.backoff_max))  # noqa: S311
                await asyncio.sleep(delay)

        raise RuntimeError("Unreachable code reached")  # mypy quirk

    @staticmethod
    def _compute_time_perf(start_time: float, end_time: float, num_samples: int) -> EvaluationTimePerf:
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

        return EvaluationTimePerf(
            total_time_in_seconds=latency,
            samples_per_second=throughput,
            latency_in_seconds=latency_sample,
        )
