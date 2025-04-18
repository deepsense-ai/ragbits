from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search import DocumentSearch
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.pipelines.base import (
    EvaluationDatapointSchemaT,
    EvaluationPipeline,
    EvaluationResult,
    EvaluationTargetT,
)
from ragbits.evaluate.pipelines.document_search import DocumentSearchPipeline

_target_to_evaluation_pipeline: dict[type[WithConstructionConfig], type[EvaluationPipeline]] = {
    DocumentSearch: DocumentSearchPipeline
}

__all__ = [
    "DocumentSearchPipeline",
    "EvaluationDatapointSchemaT",
    "EvaluationPipeline",
    "EvaluationResult",
    "EvaluationTargetT",
]


def get_evaluation_assets_for_target(
    evaluation_target: WithConstructionConfig,
) -> tuple[
    EvaluationPipeline,
    Evaluator,
]:
    """
    A function instantiating evaluation pipeline for given WithConstructionConfig object
    Args:
        evaluation_target: WithConstructionConfig object to be evaluated
    Returns:
        instance of evaluation pipeline
    Raises:
        ValueError for classes with no registered evaluation pipeline
    """
    for supported_type, evaluation_pipeline_type in _target_to_evaluation_pipeline.items():
        if isinstance(evaluation_target, supported_type):
            evaluation_pipeline: EvaluationPipeline = evaluation_pipeline_type(evaluation_target=evaluation_target)
            evaluator: Evaluator = Evaluator(pipeline_type=evaluation_pipeline.configuration_key)
            return evaluation_pipeline, evaluator
    raise ValueError(f"Evaluation pipeline not implemented for {evaluation_target.__class__}")
