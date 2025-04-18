from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.evaluate import EvaluationResult
from ragbits.evaluate.config import EvaluateConfig


class EvaluationDatapointSchema(WithConstructionConfig, BaseModel, ABC):
    """Abstraction for evaluation datapoint schema definition"""

    @classmethod
    def get_default_for_pipeline(cls, config: EvaluateConfig, pipeline_type: str) -> "EvaluationDatapointSchema":
        """
        A method extracting default schema for a pipeline
        Args:
            config: EvaluateConfig - configuration of ragbits evaluate
            pipeline_type: str - type of a pipeline
        Returns:
            EvaluationDatapointSchema
        """
        datapoint_schemas = config.default_input_schemas_for_pipelines
        schema_config = datapoint_schemas.get(pipeline_type)
        if schema_config is None:
            raise ValueError(f"No default schema for {pipeline_type}")
        return cls.subclass_from_config(ObjectConstructionConfig.model_validate(schema_config))


EvaluationDatapointSchemaT = TypeVar("EvaluationDatapointSchemaT", bound=EvaluationDatapointSchema)
EvaluationTargetT = TypeVar("EvaluationTargetT", bound=WithConstructionConfig)


class EvaluationConfig(BaseModel):
    """
    Schema for for the dict taken by `Evaluator.run_from_config` method.
    """

    dataloader: ObjectConstructionConfig
    pipeline: ObjectConstructionConfig
    metrics: dict[str, ObjectConstructionConfig]
    batch_size: int = 10


class EvaluationPipeline(Generic[EvaluationTargetT, EvaluationDatapointSchemaT], WithConstructionConfig, ABC):
    """
    Collection evaluation pipeline.
    """

    CONCURRENCY: int = 10

    def __init__(self, evaluation_target: EvaluationTargetT):
        self.evaluation_target = evaluation_target

    @abstractmethod
    async def __call__(self, data: dict, schema: EvaluationDatapointSchemaT) -> EvaluationResult:
        """
        Runs the evaluation pipeline.

        Args:
            data: The evaluation data.
            schema: a schema of a datapoint

        Returns:
            The evaluation result.
        """

    async def prepare(self) -> None:
        """
        Prepares pipeline for evaluation.
        """
        pass
