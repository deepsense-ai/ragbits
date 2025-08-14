import asyncio
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast
from unittest.mock import Mock

import pytest
from typing_extensions import Self

from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import Metric, MetricSet
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


@dataclass
class MockEvaluationResult(EvaluationResult):
    input_data: int
    processed_output: str
    is_correct: bool


class MockEvaluationData(EvaluationData):
    input_data: int


class MockEvaluationTarget(WithConstructionConfig):
    def __init__(self, model_name: str = "default") -> None:
        super().__init__()
        self.model_name = model_name


class MockEvaluationPipeline(EvaluationPipeline[MockEvaluationTarget, MockEvaluationData, MockEvaluationResult]):
    def __init__(self, evaluation_target: MockEvaluationTarget, slow: bool = False):
        super().__init__(evaluation_target)
        self._slow = slow

    async def __call__(self, data: Iterable[MockEvaluationData]) -> Iterable[MockEvaluationResult]:
        results = []
        for row in data:
            if self._slow:
                await asyncio.sleep(0.5)
            results.append(
                MockEvaluationResult(
                    input_data=row.input_data,
                    processed_output=f"{self.evaluation_target.model_name}_{row.input_data}",
                    is_correct=row.input_data % 2 == 0,
                )
            )
        return results

    @classmethod
    def from_config(cls, config: dict) -> "MockEvaluationPipeline":
        evaluation_target = WithConstructionConfig.subclass_from_config(config["evaluation_target"])
        return cls(evaluation_target=cast(MockEvaluationTarget, evaluation_target))


class MockFailingEvaluationPipeline(EvaluationPipeline[MockEvaluationTarget, MockEvaluationData, MockEvaluationResult]):
    async def __call__(self, data: Iterable[MockEvaluationData]) -> Iterable[MockEvaluationResult]:
        raise Exception("This is a test exception")


class MockDataLoader(DataLoader[MockEvaluationData]):
    def __init__(self, dataset_size: int = 4) -> None:
        super().__init__(source=Mock())
        self.dataset_size = dataset_size

    async def load(self) -> Iterable[MockEvaluationData]:
        return await self.map()

    async def map(self, *args: Any, **kwargs: Any) -> Iterable[MockEvaluationData]:  # noqa: ANN401
        return [MockEvaluationData(input_data=i) for i in range(1, self.dataset_size + 1)]

    @classmethod
    def from_config(cls, config: dict) -> Self:
        return cls(**config)


class MockMetric(Metric[MockEvaluationResult]):
    async def compute(self, results: list[MockEvaluationResult]) -> dict:  # noqa: PLR6301
        accuracy = sum(1 for r in results if r.is_correct) / len(results) if results else 0
        return {"accuracy": accuracy}


@pytest.mark.parametrize(
    ("pipeline_type", "expected_results", "expected_errors", "expected_accuracy"),
    [(MockEvaluationPipeline, 4, 0, 0.5), (MockFailingEvaluationPipeline, 0, 1, 0)],
)
async def test_run_evaluation(
    pipeline_type: type[EvaluationPipeline[MockEvaluationTarget, MockEvaluationData, MockEvaluationResult]],
    expected_results: int,
    expected_errors: int,
    expected_accuracy: float,
) -> None:
    target = MockEvaluationTarget(model_name="test_model")
    pipeline = pipeline_type(target)
    dataloader = MockDataLoader()
    metrics = MetricSet(*[MockMetric()])
    evaluator = Evaluator()

    results = await evaluator.compute(
        pipeline=pipeline,
        dataloader=dataloader,
        metricset=metrics,
    )

    assert len(results.results) == expected_results
    assert len(results.errors) == expected_errors
    assert results.metrics["accuracy"] == expected_accuracy
    assert all("test_model_" in r.processed_output for r in results.results)


@pytest.mark.parametrize(
    ("parallelize_batches", "expected_results", "expected_accuracy"),
    [(False, 4, 0.5), (True, 4, 0.5)],
)
async def test_run_evaluation_with_parallel_batches(
    parallelize_batches: bool,
    expected_results: int,
    expected_accuracy: float,
) -> None:
    target = MockEvaluationTarget(model_name="parallel_test_model")
    pipeline = MockEvaluationPipeline(target)
    dataloader = MockDataLoader()
    metrics = MetricSet(*[MockMetric()])
    evaluator = Evaluator(batch_size=2, parallelize_batches=parallelize_batches)

    results = await evaluator.compute(
        pipeline=pipeline,
        dataloader=dataloader,
        metricset=metrics,
    )

    assert len(results.results) == expected_results
    assert len(results.errors) == 0
    assert results.metrics["accuracy"] == expected_accuracy
    assert all("parallel_test_model_" in r.processed_output for r in results.results)


async def test_parallel_batches_performance() -> None:
    """Test that parallel processing is faster than sequential processing."""
    target = MockEvaluationTarget(model_name="timing_test_model")
    pipeline = MockEvaluationPipeline(target, slow=True)
    dataloader = MockDataLoader(dataset_size=4)
    metrics = MetricSet(*[MockMetric()])

    # Test sequential processing
    evaluator_sequential = Evaluator(batch_size=2, parallelize_batches=False)
    start_time = time.perf_counter()
    results_sequential = await evaluator_sequential.compute(
        pipeline=pipeline,
        dataloader=dataloader,
        metricset=metrics,
    )
    sequential_time = time.perf_counter() - start_time

    evaluator_parallel = Evaluator(batch_size=2, parallelize_batches=True)
    start_time = time.perf_counter()
    results_parallel = await evaluator_parallel.compute(
        pipeline=pipeline,
        dataloader=dataloader,
        metricset=metrics,
    )
    parallel_time = time.perf_counter() - start_time

    assert len(results_sequential.results) == len(results_parallel.results)
    assert results_sequential.metrics == results_parallel.metrics

    # Parallel processing should be roughly 2x faster, but we add some margin
    assert parallel_time < sequential_time * 0.7


async def test_run_from_config() -> None:
    config = {
        "evaluation": {
            "dataloader": ObjectConstructionConfig.model_validate(
                {"type": f"{__name__}:MockDataLoader", "config": {"dataset_size": 6}}
            ),
            "pipeline": {
                "type": f"{__name__}:MockEvaluationPipeline",
                "config": {
                    "evaluation_target": ObjectConstructionConfig.model_validate(
                        {"type": f"{__name__}:MockEvaluationTarget", "config": {"model_name": "config_model"}}
                    )
                },
            },
            "metrics": {
                "main_metric": ObjectConstructionConfig.model_validate({"type": f"{__name__}:MockMetric", "config": {}})
            },
        },
    }
    results = await Evaluator.run_from_config(config)

    assert len(results.results) == 6
    assert results.metrics["accuracy"] == 0.5
    assert all("config_model_" in r.processed_output for r in results.results)
