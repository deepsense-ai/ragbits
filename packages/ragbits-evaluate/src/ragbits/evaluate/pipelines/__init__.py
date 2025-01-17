import sys

from ragbits.core.utils.config_handling import import_by_path

from .base import EvaluationPipeline

module = sys.modules[__name__]


def pipeline_factory(config: dict) -> EvaluationPipeline:
    """
    Factory of evaluation pipelines.

    Args:
        config: Pipeline config.

    Returns:
        Instance of evaluation pipeline.
    """
    pipeline_module = import_by_path(config["type"], module)
    return pipeline_module.from_config(config["config"])
