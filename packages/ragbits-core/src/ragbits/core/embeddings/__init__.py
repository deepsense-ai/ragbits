from typing import TYPE_CHECKING

from .base import Embedder, EmbedderOptionsT, SparseVector, VectorSize
from .dense import DenseEmbedder, NoopEmbedder
from .sparse import BagOfTokens, BagOfTokensOptions, SparseEmbedder, SparseEmbedderOptionsT

if TYPE_CHECKING:
    from .dense import (
        GeminiEmbedder,
        GeminiEmbedderOptions,
        LiteLLMEmbedder,
        LiteLLMEmbedderOptions,
        OpenAIEmbedder,
        OpenAIEmbedderOptions,
        VertexAIMultimodalEmbedder,
        VertexAIMultimodalEmbedderOptions,
    )

# Provider embedders are re-exported lazily from the dense sub-package so that
# importing ragbits.core.embeddings does not pull in optional dependencies.
_LAZY: dict[str, str] = {
    "GeminiEmbedder": "ragbits.core.embeddings.dense",
    "GeminiEmbedderOptions": "ragbits.core.embeddings.dense",
    "LiteLLMEmbedder": "ragbits.core.embeddings.dense",
    "LiteLLMEmbedderOptions": "ragbits.core.embeddings.dense",
    "OpenAIEmbedder": "ragbits.core.embeddings.dense",
    "OpenAIEmbedderOptions": "ragbits.core.embeddings.dense",
    "VertexAIMultimodalEmbedder": "ragbits.core.embeddings.dense",
    "VertexAIMultimodalEmbedderOptions": "ragbits.core.embeddings.dense",
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
    "GeminiEmbedder",
    "GeminiEmbedderOptions",
    "LiteLLMEmbedder",
    "LiteLLMEmbedderOptions",
    "NoopEmbedder",
    "OpenAIEmbedder",
    "OpenAIEmbedderOptions",
    "SparseEmbedder",
    "SparseEmbedderOptionsT",
    "SparseVector",
    "VectorSize",
    "VertexAIMultimodalEmbedder",
    "VertexAIMultimodalEmbedderOptions",
]
