import sys

from omegaconf import DictConfig

from ragbits.core.utils.config_handling import import_by_path

from .base import EvaluationPipeline

module = sys.modules[__name__]


def pipeline_factory(pipeline_config: dict) -> EvaluationPipeline:
    """
    Factory of evaluation pipelines
    Args:
        pipeline_config: DictConfig
    Returns:
        instance of evaluation pipeline
    """
    pipeline_module = import_by_path(pipeline_config["type"], module)
    config = {"config": pipeline_config}
    pipeline = pipeline_module.from_config(config)
    return pipeline
