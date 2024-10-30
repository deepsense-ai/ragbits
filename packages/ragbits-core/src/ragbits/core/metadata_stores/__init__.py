import sys

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import MetadataStore
from .in_memory import InMemoryMetadataStore

__all__ = ["InMemoryMetadataStore", "MetadataStore"]

module = sys.modules[__name__]


def get_metadata_store(metadata_store_config: dict | None) -> MetadataStore | None:
    """
    Initializes and returns a MetadataStore object based on the provided configuration.

    Args:
        metadata_store_config: A dictionary containing configuration details for the MetadataStore.

    Returns:
        An instance of the specified MetadataStore class, initialized with the provided config
        (if any) or default arguments.
    """
    if metadata_store_config is None:
        return None

    metadata_store_class = get_cls_from_config(metadata_store_config["type"], module)
    config = metadata_store_config.get("config", {})

    return metadata_store_class(**config)
