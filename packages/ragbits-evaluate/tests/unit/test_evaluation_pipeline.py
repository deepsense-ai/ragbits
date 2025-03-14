from dataclasses import dataclass
from typing import cast

import pytest
from datasets import Dataset

from ragbits.core.utils.config_handling import ObjectContructionConfig, WithConstructionConfig
from ragbits.evaluate import EvaluationResult
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import Metric, MetricSet
from ragbits.evaluate.pipelines.base import EvaluationDatapointSchema, EvaluationPipeline


@dataclass
class MockEvaluationResult(EvaluationResult):
    input_data: int
    processed_output: str
    is_correct: bool


class MockEvaluationTarget(WithConstructionConfig):
    def __init__(self, model_name: str = "default"):
        super().__init__()
        self.model_name = model_name


class MockEvaluationSchema(EvaluationDatapointSchema):
    input_col: str


class MockEvaluationPipeline(EvaluationPipeline[MockEvaluationTarget, MockEvaluationSchema]):
    configuration_key = "test"

    async def __call__(self, data: dict, schema: MockEvaluationSchema) -> MockEvaluationResult:
        return MockEvaluationResult(
            input_data=data[schema.input_col],
            processed_output=f"{self.evaluation_target.model_name}_{data[schema.input_col]}",
            is_correct=data[schema.input_col] % 2 == 0,
        )

    @classmethod
    def from_config(cls, config: dict) -> "MockEvaluationPipeline":
        evaluation_target = WithConstructionConfig.subclass_from_config(config["evaluation_target"])
        return cls(evaluation_target=cast(MockEvaluationTarget, evaluation_target))


class MockDataLoader(DataLoader):
    def __init__(self, dataset_size: int = 4):
        super().__init__()
        self.dataset_size = dataset_size

    async def load(self) -> Dataset:
        return Dataset.from_dict({"input": list(range(1, self.dataset_size + 1))})


class MockMetric(Metric):
    def compute(self, results: list[MockEvaluationResult]) -> dict:  # noqa: PLR6301
        accuracy = sum(1 for r in results if r.is_correct) / len(results)
        return {"accuracy": accuracy}


@pytest.fixture
def experiment_config() -> dict:
    config = {
        "dataloader": ObjectContructionConfig.model_validate(
            {"type": f"{__name__}:MockDataLoader", "config": {"dataset_size": 3}}
        ),
        "pipeline": {
            "type": f"{__name__}:MockEvaluationPipeline",
            "config": {
                "evaluation_target": ObjectContructionConfig.model_validate(
                    {"type": f"{__name__}:MockEvaluationTarget", "config": {"model_name": "config_model"}}
                )
            },
        },
        "metrics": {
            "main_metric": ObjectContructionConfig.model_validate({"type": f"{__name__}:MockMetric", "config": {}})
        },
    }
    return config


@pytest.fixture
def datapoint_schema_config() -> dict:
    return {"type": f"{__name__}:MockEvaluationSchema", "config": {"input_col": "input"}}


@pytest.mark.asyncio
async def test_run_evaluation(datapoint_schema_config: dict) -> None:
    target: MockEvaluationTarget = MockEvaluationTarget(model_name="test_model")
    pipeline: MockEvaluationPipeline = MockEvaluationPipeline(target)
    loader: MockDataLoader = MockDataLoader()
    metrics: MetricSet = MetricSet(*[MockMetric()])
    evaluator: Evaluator = Evaluator(schema_config=datapoint_schema_config)

    results = await evaluator.compute(pipeline, loader, metrics)

    assert len(results["results"]) == 4
    assert 0 <= results["metrics"]["accuracy"] <= 1
    assert all("test_model_" in r["processed_output"] for r in results["results"])


@pytest.mark.asyncio
async def test_result_structure(datapoint_schema_config) -> None:
    target = MockEvaluationTarget()
    pipeline = MockEvaluationPipeline(target)
    schema = EvaluationDatapointSchema.subclass_from_config(
        ObjectContructionConfig.model_validate(datapoint_schema_config)
    )
    result = await pipeline({"input": 2}, schema=schema)  # type: ignore[arg-type]

    assert isinstance(result, MockEvaluationResult)
    assert result.is_correct is True
    assert "2" in result.processed_output


@pytest.mark.asyncio
async def test_run_from_config(experiment_config: dict) -> None:
    results = await Evaluator.run_from_config(experiment_config)
    assert len(results["results"]) == 3
    assert all("config_model_" in r["processed_output"] for r in results["results"])
