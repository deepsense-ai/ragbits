import sys

from omegaconf import ListConfig

from ragbits.core.utils.config_handling import import_by_path

from .base import MetricSet

module = sys.modules[__name__]


def metric_set_factory(cfg: list[dict]) -> MetricSet:
    """
    A function creating MetricSet instance from the configuration
    Args:
        cfg - metric cnfiguration
    Returns:
        MetricSet
    """
    metrics = []
    for metric_cfg in cfg:
        metric_module = import_by_path(metric_cfg["type"], module)
        metrics.append(metric_module.from_config({"config": metric_cfg}))
    return MetricSet(*metrics)
