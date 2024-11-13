import sys

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import ProcessingExecutionStrategy
from .batched import BatchedAsyncProcessing
from .sequential import SequentialProcessing

__all__ = ["BatchedAsyncProcessing", "ProcessingExecutionStrategy", "SequentialProcessing"]


def get_processing_strategy(config: dict | None = None) -> ProcessingExecutionStrategy:
    """
    Initializes and returns a ProcessingExecutionStrategy object based on the provided configuration.

    Args:
        config: A dictionary containing configuration details for the ProcessingExecutionStrategy.

    Returns:
        An instance of the specified ProcessingExecutionStrategy class, initialized with the provided config
        (if any) or default arguments.

    Raises:
        KeyError: If the provided configuration does not contain a valid "type" key.
        InvalidConfigurationError: If the provided configuration is invalid.
        NotImplementedError: If the specified ProcessingExecutionStrategy class cannot be created from
            the provided configuration.
    """
    if config is None:
        return SequentialProcessing()

    strategy_cls = get_cls_from_config(config["type"], sys.modules[__name__])
    return strategy_cls.from_config(config.get("config", {}))
