from typing import TYPE_CHECKING

from .base import DenseEmbedder
from .noop import NoopEmbedder

if TYPE_CHECKING:
    from .litellm import LiteLLMEmbedder, LiteLLMEmbedderOptions

# LiteLLMEmbedder is loaded lazily to avoid importing the optional ``litellm``
# dependency at package-import time.
_LAZY: dict[str, str] = {
    "LiteLLMEmbedder": "ragbits.core.embeddings.dense.litellm",
    "LiteLLMEmbedderOptions": "ragbits.core.embeddings.dense.litellm",
}


def __getattr__(name: str) -> object:
    if name in _LAZY:
        import importlib

        module = importlib.import_module(_LAZY[name])
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'ragbits.core.embeddings.dense' has no attribute {name!r}")


__all__ = [
    "DenseEmbedder",
    "LiteLLMEmbedder",
    "LiteLLMEmbedderOptions",
    "NoopEmbedder",
]
