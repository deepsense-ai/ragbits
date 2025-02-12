from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.evaluate.evaluation_target import EvaluationTarget

DEFAULT_EVAL_TARGET_CONFIG = {
    "metrics_config": {
        "precision_recall_f1": ObjectContructionConfig.model_validate(
            {
                "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
                "config": {
                    "matching_strategy": {
                        "type": "RougeChunkMatch",
                        "config": {
                            "threshold": 0.5,
                        },
                    },
                },
            }
        ),
    },
    "dataloader_config": {
        "type": "ragbits.evaluate.dataloaders.hf:HFDataLoader",
        "config": {
            "path": "micpst/hf-docs-retrieval",
            "split": "train",
        },
    },
}


def default_evaluation_target() -> EvaluationTarget:
    """Default factory for evaluation target"""
    return EvaluationTarget.from_config(config=DEFAULT_EVAL_TARGET_CONFIG)
