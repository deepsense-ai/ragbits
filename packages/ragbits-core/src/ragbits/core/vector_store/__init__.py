import sys

from ..utils.config_handling import get_cls_from_config
from .base import VectorDBEntry, VectorStore
from .chromadb_store import ChromaDBStore
from .in_memory import InMemoryVectorStore

__all__ = ["ChromaDBStore", "InMemoryVectorStore", "VectorDBEntry", "VectorStore"]

module = sys.modules[__name__]


def get_vector_store(vector_store_config: dict) -> VectorStore:
    """
    Initializes and returns a VectorStore object based on the provided configuration.

    Args:
        vector_store_config: A dictionary containing configuration details for the VectorStore.

    Returns:
        An instance of the specified VectorStore class, initialized with the provided config
        (if any) or default arguments.
    """
    vector_store_cls = get_cls_from_config(vector_store_config["type"], module)
    config = vector_store_config.get("config", {})

    if vector_store_config["type"] == "ChromaDBStore":
        return vector_store_cls.from_config(config)

    return vector_store_cls(**config)
