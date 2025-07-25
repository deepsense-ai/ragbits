import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from .base import LLM, ToolCall, Usage
from .local import LocalLLM, LocalLLMOptions

_import_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="litellm-import")
_litellm_future = None
_import_lock = threading.Lock()


@lru_cache(maxsize=None)
def _import_litellm():
    from .litellm import LiteLLM, LiteLLMOptions
    return LiteLLM, LiteLLMOptions


def _start_litellm_import():
    global _litellm_future
    with _import_lock:
        if _litellm_future is None:
            _litellm_future = _import_executor.submit(_import_litellm)


def __getattr__(name: str):
    if name in ("LiteLLM", "LiteLLMOptions"):
        _start_litellm_import()
        LiteLLM, LiteLLMOptions = _litellm_future.result()

        if name == "LiteLLM":
            return LiteLLM
        elif name == "LiteLLMOptions":
            return LiteLLMOptions

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["LLM", "LiteLLM", "LiteLLMOptions", "LocalLLM", "LocalLLMOptions", "ToolCall", "Usage"]