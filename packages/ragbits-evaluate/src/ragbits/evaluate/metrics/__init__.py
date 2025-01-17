import sys

from ragbits.core.utils.config_handling import import_by_path

from .base import MetricSet

module = sys.modules[__name__]


def metric_set_factory(config: list[dict]) -> MetricSet:
    """
    A function creating MetricSet instance from the configuration.

    Args:
        config: Metric configuration.

    Returns:
        Metric set.
    """
    metrics = []
    for metric_config in config:
        metric_module = import_by_path(metric_config["type"], module)
        metrics.append(metric_module.from_config(metric_config["config"]))
    return MetricSet(*metrics)
