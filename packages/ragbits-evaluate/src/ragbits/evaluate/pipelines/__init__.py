import sys

from omegaconf import DictConfig

from ragbits.core.utils.config_handling import import_by_path

from .base import EvaluationPipeline

module = sys.modules[__name__]


def pipeline_factory(pipeline_config: DictConfig) -> EvaluationPipeline:
    pipeline_module = import_by_path(pipeline_config.type, module)
    pipeline = pipeline_module(pipeline_config)
    return pipeline
