from typing import TYPE_CHECKING

from .base import LLM, ToolCall, Usage
from .litellm import LiteLLM, LiteLLMOptions
from .local import LocalLLM, LocalLLMOptions

if TYPE_CHECKING:
    from .anthropic import AnthropicLLM, AnthropicLLMOptions
    from .gemini import GeminiLLM, GeminiLLMOptions
    from .openai import OpenAILLM, OpenAILLMOptions

# OpenAILLM, AnthropicLLM, GeminiLLM and their Options classes are loaded lazily
# to avoid pulling in optional dependencies (openai, anthropic, google-genai) at
# package-import time — consistent with how LiteLLM uses LazyLiteLLM.
_LAZY: dict[str, str] = {
    "AnthropicLLM": "ragbits.core.llms.anthropic",
    "AnthropicLLMOptions": "ragbits.core.llms.anthropic",
    "GeminiLLM": "ragbits.core.llms.gemini",
    "GeminiLLMOptions": "ragbits.core.llms.gemini",
    "OpenAILLM": "ragbits.core.llms.openai",
    "OpenAILLMOptions": "ragbits.core.llms.openai",
}


def __getattr__(name: str) -> object:
    if name in _LAZY:
        import importlib

        module = importlib.import_module(_LAZY[name])
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'ragbits.core.llms' has no attribute {name!r}")


__all__ = [
    "LLM",
    "AnthropicLLM",
    "AnthropicLLMOptions",
    "GeminiLLM",
    "GeminiLLMOptions",
    "LiteLLM",
    "LiteLLMOptions",
    "LocalLLM",
    "LocalLLMOptions",
    "OpenAILLM",
    "OpenAILLMOptions",
    "ToolCall",
    "Usage",
]
