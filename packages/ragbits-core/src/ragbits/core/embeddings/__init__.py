from typing import TYPE_CHECKING

from .base import Embedder, EmbedderOptionsT, SparseVector, VectorSize
from .dense import DenseEmbedder, NoopEmbedder
from .sparse import BagOfTokens, BagOfTokensOptions, SparseEmbedder, SparseEmbedderOptionsT

if TYPE_CHECKING:
    from .dense import LiteLLMEmbedder

_LAZY: dict[str, str] = {
    "LiteLLMEmbedder": "ragbits.core.embeddings.dense",
}


def __getattr__(name: str) -> object:
    if name in _LAZY:
        import importlib

        module = importlib.import_module(_LAZY[name])
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'ragbits.core.embeddings' has no attribute {name!r}")


__all__ = [
    "BagOfTokens",
    "BagOfTokensOptions",
    "DenseEmbedder",
    "Embedder",
    "EmbedderOptionsT",
    "LiteLLMEmbedder",
    "NoopEmbedder",
    "SparseEmbedder",
    "SparseEmbedderOptionsT",
    "SparseVector",
    "VectorSize",
]
