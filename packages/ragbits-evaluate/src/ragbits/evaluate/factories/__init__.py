from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.evaluate.metrics import MetricSet

DS_PRECISION_RECALL_F1 = {
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
}


def precision_recall_f1() -> MetricSet:
    """A factory of precision recall f1 metric set for retrival evaluation"""
    return MetricSet.from_config(config=DS_PRECISION_RECALL_F1)
