from dataclasses import dataclass

import pytest
from datasets import Dataset
from pydantic import BaseModel
from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.pipelines.base import EvaluationPipeline
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.metrics.base import Metric, MetricSet
from ragbits.evaluate import EvaluationResult
from ragbits.core.utils.config_handling import WithConstructionConfig, ObjectContructionConfig


@dataclass
class MockEvaluationResult(EvaluationResult):
    input_data: int
    is_correct: bool


class MockEvaluationTargetConfig(BaseModel):
    threshold: float


class MockEvaluationTarget(WithConstructionConfig):
    def __init__(self, threshold: float):
        super().__init__()
        self.threshold = threshold


class MockEvaluationPipeline(EvaluationPipeline[MockEvaluationTarget]):
    CONCURRENCY = 2

    async def __call__(self, data: dict) -> MockEvaluationResult:
        return MockEvaluationResult(
            input_data=data["input"], is_correct=data["input"] >= self.evaluation_target.threshold
        )

    @classmethod
    def from_config(cls, config: dict) -> "MockEvaluationPipeline":
        evaluation_target = MockEvaluationTarget.from_config(config["evaluation_target"])
        return cls(evaluation_target=evaluation_target)


class MockDataLoader(DataLoader):
    configuration_key = "mock_loader"

    def __init__(self, dataset_size: int = 4):
        super().__init__()
        self.dataset_size = dataset_size

    async def load(self):
        return Dataset.from_dict({"input": list(range(1, self.dataset_size + 1))})


class MockMetric(Metric):
    configuration_key = "mock_metrics"

    def compute(self, results: list[MockEvaluationResult]) -> dict:
        accuracy = sum(1 for r in results if r.is_correct) / len(results)
        return {"accuracy": accuracy}


@pytest.fixture()
def optimization_config():
    return {
        "evaluation_target": {"threshold": {"optimize": True, "range": [5, 20]}},
    }


@pytest.mark.parametrize(("direction"), ["maximize", "minimize"])
def test_optimization(direction, optimization_config):
    optimizer = Optimizer(direction=direction, n_trials=2)
    ordered_configs = optimizer.optimize(
        pipeline_class=MockEvaluationPipeline,
        pipeline_config=optimization_config,
        dataloader=MockDataLoader(dataset_size=30),
        metrics=MetricSet(*[MockMetric()]),
    )
    worse_val = ordered_configs[1][1]
    better_val = ordered_configs[0][1]
    if direction == "maximize":
        assert worse_val <= better_val
    else:
        assert better_val <= worse_val
    assert MockEvaluationTargetConfig.model_validate(ordered_configs[0][0]["evaluation_target"])
    assert MockEvaluationTargetConfig.model_validate(ordered_configs[1][0]["evaluation_target"])


