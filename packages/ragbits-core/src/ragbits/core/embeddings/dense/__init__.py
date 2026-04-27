from typing import TYPE_CHECKING

from .base import DenseEmbedder
from .noop import NoopEmbedder

if TYPE_CHECKING:
    from .gemini import GeminiEmbedder, GeminiEmbedderOptions
    from .litellm import LiteLLMEmbedder, LiteLLMEmbedderOptions
    from .openai import OpenAIEmbedder, OpenAIEmbedderOptions
    from .vertex_multimodal import VertexAIMultimodalEmbedder, VertexAIMultimodalEmbedderOptions

# Provider embedders are loaded lazily to avoid importing optional dependencies
# (openai, google-genai, google-auth, litellm) at package-import time.
_LAZY: dict[str, str] = {
    "GeminiEmbedder": "ragbits.core.embeddings.dense.gemini",
    "GeminiEmbedderOptions": "ragbits.core.embeddings.dense.gemini",
    "LiteLLMEmbedder": "ragbits.core.embeddings.dense.litellm",
    "LiteLLMEmbedderOptions": "ragbits.core.embeddings.dense.litellm",
    "OpenAIEmbedder": "ragbits.core.embeddings.dense.openai",
    "OpenAIEmbedderOptions": "ragbits.core.embeddings.dense.openai",
    "VertexAIMultimodalEmbedder": "ragbits.core.embeddings.dense.vertex_multimodal",
    "VertexAIMultimodalEmbedderOptions": "ragbits.core.embeddings.dense.vertex_multimodal",
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
    "GeminiEmbedder",
    "GeminiEmbedderOptions",
    "LiteLLMEmbedder",
    "LiteLLMEmbedderOptions",
    "NoopEmbedder",
    "OpenAIEmbedder",
    "OpenAIEmbedderOptions",
    "VertexAIMultimodalEmbedder",
    "VertexAIMultimodalEmbedderOptions",
]
