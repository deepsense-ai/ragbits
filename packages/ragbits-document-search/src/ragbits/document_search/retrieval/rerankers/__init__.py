import sys
from typing import Optional

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import Reranker
from .noop import NoopReranker

__all__ = ["NoopReranker", "Reranker"]

module = sys.modules[__name__]


def get_reranker(reranker_config: Optional[dict]) -> Reranker:
    """
    Initializes and returns a Reranker object based on the provided configuration.

    Args:
        reranker_config: A dictionary containing configuration details for the Reranker.

    Returns:
        An instance of the specified Reranker class, initialized with the provided config
        (if any) or default arguments.
    """

    if reranker_config is None:
        return NoopReranker()

    reranker_cls = get_cls_from_config(reranker_config["type"], module)
    config = reranker_config.get("config", {})

    return reranker_cls(**config)
