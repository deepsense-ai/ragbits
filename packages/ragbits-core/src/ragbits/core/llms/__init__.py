from typing import TYPE_CHECKING

from .base import LLM, ToolCall, Usage
from .local import LocalLLM, LocalLLMOptions

if TYPE_CHECKING:
    from .anthropic import AnthropicLLM, AnthropicLLMOptions
    from .gemini import GeminiLLM, GeminiLLMOptions
    from .litellm import LiteLLM, LiteLLMOptions
    from .openai import OpenAILLM, OpenAILLMOptions

# Provider-specific LLMs and their Options classes are loaded lazily to avoid
# pulling in optional dependencies (openai, anthropic, google-genai, litellm)
# at package-import time.
_LAZY: dict[str, str] = {
    "AnthropicLLM": "ragbits.core.llms.anthropic",
    "AnthropicLLMOptions": "ragbits.core.llms.anthropic",
    "GeminiLLM": "ragbits.core.llms.gemini",
    "GeminiLLMOptions": "ragbits.core.llms.gemini",
    "LiteLLM": "ragbits.core.llms.litellm",
    "LiteLLMOptions": "ragbits.core.llms.litellm",
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
