import sys

from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.document_search.retrieval.rerankers.base import Reranker
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker

__all__ = ["NoopReranker", "Reranker"]


def get_reranker(config: dict | None = None) -> Reranker:
    """
    Initializes and returns a Reranker object based on the provided configuration.

    Args:
        config: A dictionary containing configuration details for the Reranker.

    Returns:
        An instance of the specified Reranker class, initialized with the provided config
        (if any) or default arguments.

    Raises:
        KeyError: If the provided configuration does not contain a valid "type" key.
        InvalidConfigurationError: If the provided configuration is invalid.
        NotImplementedError: If the specified Reranker class cannot be created from the provided configuration.
    """
    if config is None:
        return NoopReranker()

    reranker_cls = get_cls_from_config(config["type"], sys.modules[__name__])
    return reranker_cls.from_config(config.get("config", {}))
