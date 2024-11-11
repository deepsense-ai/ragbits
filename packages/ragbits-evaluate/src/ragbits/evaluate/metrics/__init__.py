import sys

from omegaconf import ListConfig

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import MetricSet

module = sys.modules[__name__]


def metric_set_factory(cfg: ListConfig) -> MetricSet:
    """
    A function creating MetricSet instance from the configuration
    Args:
        cfg - metric cnfiguration
    Returns:
        MetricSet
    """
    metrics = []
    for metric_cfg in cfg:
        metric_module = get_cls_from_config(metric_cfg.type, module)
        metrics.append(metric_module(metric_cfg))
    return MetricSet(*metrics)
