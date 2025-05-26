from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.metrics.base import Metric, MetricSet
from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


@dataclass
class MockEvaluationResult(EvaluationResult):
    input_data: int
    is_correct: bool


class MockEvaluationData(EvaluationData):
    input_data: int


class MockEvaluationTargetConfig(BaseModel):
    threshold: float


class MockEvaluationTarget(WithConstructionConfig):
    def __init__(self, threshold: float) -> None:
        super().__init__()
        self.threshold = threshold


class MockEvaluationPipeline(EvaluationPipeline[MockEvaluationTarget, MockEvaluationData, MockEvaluationResult]):
    async def __call__(self, data: Iterable[MockEvaluationData]) -> Iterable[MockEvaluationResult]:
        return [
            MockEvaluationResult(
                input_data=row.input_data,
                is_correct=row.input_data >= self.evaluation_target.threshold,
            )
            for row in data
        ]

    @classmethod
    def from_config(cls, config: dict) -> "MockEvaluationPipeline":
        evaluation_target = MockEvaluationTarget.from_config(config["evaluation_target"])
        return cls(evaluation_target=evaluation_target)


class MockDataLoader(DataLoader):
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


class MockMetric(Metric):
    async def compute(self, results: list[MockEvaluationResult]) -> dict:  # noqa: PLR6301
        accuracy = sum(1 for r in results if r.is_correct) / len(results)
        return {"accuracy": accuracy}


@pytest.mark.parametrize(("direction"), ["maximize", "minimize"])
def test_optimization(direction: str) -> None:
    pipeline_config = {"evaluation_target": {"threshold": {"optimize": True, "range": [5, 20]}}}
    optimizer = Optimizer(direction=direction, n_trials=2)
    ordered_results = optimizer.optimize(
        pipeline_class=MockEvaluationPipeline,
        pipeline_config=pipeline_config,
        dataloader=MockDataLoader(dataset_size=30),
        metricset=MetricSet(*[MockMetric()]),
    )

    assert MockEvaluationTargetConfig.model_validate(ordered_results[0][0]["evaluation_target"])
    assert MockEvaluationTargetConfig.model_validate(ordered_results[1][0]["evaluation_target"])
    worse_val = ordered_results[1][0]["evaluation_target"]["threshold"]
    better_val = ordered_results[0][0]["evaluation_target"]["threshold"]
    if direction == "maximize":
        assert better_val <= worse_val
    else:
        assert worse_val <= better_val


def test_optimization_from_config() -> None:
    config = {
        "optimizer": {
            "direction": "maximize",
            "n_trials": 5,
            "max_retries_for_trial": 1,
        },
        "evaluator": {
            "evaluation": {
                "pipeline": {
                    "type": f"{__name__}:MockEvaluationPipeline",
                    "config": {
                        "evaluation_target": {"threshold": {"optimize": True, "range": [5, 20]}},
                    },
                },
                "dataloader": {"type": f"{__name__}:MockDataLoader", "config": {"dataset_size": 30}},
                "metrics": {"test": {"type": f"{__name__}:MockMetric", "config": {}}},
            },
        },
    }
    ordered_resuls = Optimizer.run_from_config(config)

    assert len(ordered_resuls) == 5
    best_val = float("inf")
    for res in ordered_resuls[::-1]:
        assert MockEvaluationTargetConfig.model_validate(res[0]["evaluation_target"])
        val = res[0]["evaluation_target"]["threshold"]
        assert val <= best_val
        best_val = val
