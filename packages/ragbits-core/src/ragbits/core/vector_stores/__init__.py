import sys

from ..metadata_stores import get_metadata_store
from ..utils.config_handling import get_cls_from_config
from .base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery
from .in_memory import InMemoryVectorStore

__all__ = ["InMemoryVectorStore", "VectorStore", "VectorStoreEntry", "WhereQuery"]

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

    if vector_store_config["type"].endswith(("ChromaVectorStore", "QdrantVectorStore")):
        return vector_store_cls.from_config(config)

    metadata_store_config = vector_store_config.get("metadata_store_config")
    return vector_store_cls(
        default_options=VectorStoreOptions(**config.get("default_options", {})),
        metadata_store=get_metadata_store(metadata_store_config),
    )
