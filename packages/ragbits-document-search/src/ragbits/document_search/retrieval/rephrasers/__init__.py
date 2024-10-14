import sys
from typing import Optional

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import QueryRephraser
from .noop import NoopQueryRephraser

__all__ = ["NoopQueryRephraser", "QueryRephraser"]

module = sys.modules[__name__]


def get_rephraser(rephraser_config: Optional[dict]) -> QueryRephraser:
    """
    Initializes and returns a QueryRephraser object based on the provided configuration.

    Args:
        rephraser_config: A dictionary containing configuration details for the QueryRephraser.

    Returns:
        An instance of the specified QueryRephraser class, initialized with the provided config
        (if any) or default arguments.
    """

    if rephraser_config is None:
        return NoopQueryRephraser()

    rephraser_cls = get_cls_from_config(rephraser_config["type"], module)
    config = rephraser_config.get("config", {})

    return rephraser_cls(**config)
