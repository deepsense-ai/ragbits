import sys

from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore

__all__ = ["InMemoryVectorStore", "VectorStore", "VectorStoreEntry", "VectorStoreOptions", "WhereQuery"]


def get_vector_store(config: dict) -> VectorStore:
    """
    Initializes and returns a VectorStore object based on the provided configuration.

    Args:
        config: A dictionary containing configuration details for the VectorStore.

    Returns:
        An instance of the specified VectorStore class, initialized with the provided config
        (if any) or default arguments.

    Raises:
        KeyError: If the provided configuration does not contain a valid "type" key.
        InvalidConfigurationError: If the provided configuration is invalid.
        NotImplementedError: If the specified VectorStore class cannot be created from the provided configuration.
    """
    vector_store_cls = get_cls_from_config(config["type"], sys.modules[__name__])
    return vector_store_cls.from_config(config.get("config", {}))
