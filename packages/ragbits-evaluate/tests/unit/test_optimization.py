from dataclasses import dataclass

import pytest
from datasets import Dataset
from pydantic import BaseModel

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate import EvaluationResult
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.metrics.base import Metric, MetricSet
from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.pipelines.base import EvaluationPipeline


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

    async def load(self) -> Dataset:
        return Dataset.from_dict({"input": list(range(1, self.dataset_size + 1))})


class MockMetric(Metric):
    configuration_key = "mock_metrics"

    def compute(self, results: list[MockEvaluationResult]) -> dict:
        accuracy = sum(1 for r in results if r.is_correct) / len(results)
        return {"accuracy": accuracy}


@pytest.fixture
def eval_pipeline_config() -> dict:
    return {
        "evaluation_target": {"threshold": {"optimize": True, "range": [5, 20]}},
    }


@pytest.fixture
def experiment_config(eval_pipeline_config: dict) -> dict:
    config = {
        "optimizer": {
            "direction": "maximize",
            "n_trials": 5,
            "max_retries_for_trial": 1,
        },
        "experiment": {
            "pipeline": {"type": f"{__name__}:MockEvaluationPipeline", "config": eval_pipeline_config},
            "dataloader": {"type": f"{__name__}:MockDataLoader", "config": {"dataset_size": 30}},
            "metrics": {"test": {"type": f"{__name__}:MockMetric", "config": {}}},
        },
    }
    return config


@pytest.mark.parametrize(("direction"), ["maximize", "minimize"])
def test_optimization(direction: str, eval_pipeline_config: dict) -> None:
    optimizer = Optimizer(direction=direction, n_trials=2)
    ordered_results = optimizer.optimize(
        pipeline_class=MockEvaluationPipeline,
        pipeline_config=eval_pipeline_config,
        dataloader=MockDataLoader(dataset_size=30),
        metrics=MetricSet(*[MockMetric()]),
    )
    worse_val = ordered_results[1][1]
    better_val = ordered_results[0][1]
    if direction == "maximize":
        assert worse_val <= better_val
    else:
        assert better_val <= worse_val
    assert MockEvaluationTargetConfig.model_validate(ordered_results[0][0]["evaluation_target"])
    assert MockEvaluationTargetConfig.model_validate(ordered_results[1][0]["evaluation_target"])


def test_optimization_from_config(experiment_config: dict) -> None:
    ordered_resuls = Optimizer.run_from_config(experiment_config)
    assert len(ordered_resuls) == 5
    for res in ordered_resuls:
        assert MockEvaluationTargetConfig.model_validate(res[0]["evaluation_target"])
