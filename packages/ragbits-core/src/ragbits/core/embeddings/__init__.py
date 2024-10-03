import sys

from .base import Embeddings
from .litellm import LiteLLMEmbeddings
from .local import LocalEmbeddings

__all__ = ["LiteLLMEmbeddings", "LocalEmbeddings"]

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
    config = embedder_config.get("config")

    if config is None:
        return getattr(module, embeddings_type)()
    return getattr(module, embeddings_type)(**config)
