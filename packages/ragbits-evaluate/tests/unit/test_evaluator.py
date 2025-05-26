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
    async def __call__(self, data: Iterable[MockEvaluationData]) -> Iterable[MockEvaluationResult]:
        return [
            MockEvaluationResult(
                input_data=row.input_data,
                processed_output=f"{self.evaluation_target.model_name}_{row.input_data}",
                is_correct=row.input_data % 2 == 0,
            )
            for row in data
        ]

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
