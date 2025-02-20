from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search import DocumentSearch
from ragbits.evaluate.pipelines.base import EvaluationPipeline, EvaluationResult
from ragbits.evaluate.pipelines.document_search import DocumentSearchPipeline



_target_to_evaluation_pipeline = {DocumentSearch: DocumentSearchPipeline}

__all__ = ["EvaluationPipeline", "EvaluationResult", "DocumentSearchPipeline"]


def get_evaluation_pipeline_for_target(evaluation_target: WithConstructionConfig) -> EvaluationPipeline:
    for supported_type in _target_to_evaluation_pipeline:
        if isinstance(evaluation_target, supported_type):
            return EvaluationPipeline(evaluation_target)
    raise ValueError(f"Evaluation pipeline not implemented for {evaluation_target.__class__}")



