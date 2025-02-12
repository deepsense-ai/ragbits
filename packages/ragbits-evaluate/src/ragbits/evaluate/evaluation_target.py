from typing import ClassVar

from ragbits.core.utils.config_handling import ObjectContructionConfig, WithConstructionConfig
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.metrics.base import MetricSet


class EvaluationTarget(WithConstructionConfig):
    """A class defining an evaluation target"""
    configuration_key: ClassVar = "evaluation_target"

    def __init__(self, metrics_config: dict, dataloader_config: dict):
        self.metrics: MetricSet = MetricSet.from_config(metrics_config)
        self.dataloader: DataLoader = DataLoader.subclass_from_config(
            ObjectContructionConfig.model_validate(dataloader_config)
        )
