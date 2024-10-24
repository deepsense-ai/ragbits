import sys

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import Embeddings
from .noop import NoopEmbeddings

__all__ = ["Embeddings", "NoopEmbeddings"]

module = sys.modules[__name__]


def get_embeddings(embedder_config: dict) -> Embeddings:
    """
    Initializes and returns an Embeddings object based on the provided embedder configuration.

    Args:
        embedder_config : A dictionary containing configuration details for the embedder.

    Returns:
        An instance of the specified Embeddings class, initialized with the provided config
        (if any) or default arguments.
    """
    embeddings_type = embedder_config["type"]
    config = embedder_config.get("config", {})

    embbedings = get_cls_from_config(embeddings_type, module)
    return embbedings(**config)
