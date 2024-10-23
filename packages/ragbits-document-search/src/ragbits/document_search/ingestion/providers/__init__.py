import sys

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import BaseProvider
from .dummy import DummyProvider
from .unstructured.default import UnstructuredDefaultProvider
from .unstructured.images import UnstructuredImageProvider
from .unstructured.pdf import UnstructuredPdfProvider

__all__ = [
    "BaseProvider",
    "DummyProvider",
    "UnstructuredDefaultProvider",
    "UnstructuredPdfProvider",
    "UnstructuredImageProvider",
]

module = sys.modules[__name__]


def get_provider(provider_config: dict) -> BaseProvider:
    """
    Initializes and returns a Provider object based on the provided configuration.

    Args:
        provider_config : A dictionary containing configuration details for the provider.

    Returns:
        An instance of the specified Provider class, initialized with the provided config
        (if any) or default arguments.
    """

    provider_cls = get_cls_from_config(provider_config["type"], module)
    config = provider_config.get("config", {})

    return provider_cls(**config)
