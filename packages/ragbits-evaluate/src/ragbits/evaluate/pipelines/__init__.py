from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search import DocumentSearch
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult
from ragbits.evaluate.pipelines.document_search import DocumentSearchPipeline

__all__ = ["DocumentSearchPipeline", "EvaluationData", "EvaluationPipeline", "EvaluationResult"]

_target_to_evaluation_pipeline: dict[type[WithConstructionConfig], type[EvaluationPipeline]] = {
    DocumentSearch: DocumentSearchPipeline,
}


def get_evaluation_pipeline_for_target(evaluation_target: WithConstructionConfig) -> EvaluationPipeline:
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
            return evaluation_pipeline_type(evaluation_target=evaluation_target)
    raise ValueError(f"Evaluation pipeline not implemented for {evaluation_target.__class__}")
