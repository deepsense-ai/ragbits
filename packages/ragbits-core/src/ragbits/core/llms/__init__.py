import threading
from concurrent.futures import Future, ThreadPoolExecutor
from functools import cache

from .base import LLM, ToolCall, Usage
from .local import LocalLLM, LocalLLMOptions

_import_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="litellm-import")
_litellm_future: Future[tuple[type, type]] | None = None
_import_lock = threading.Lock()


@cache
def _import_litellm() -> tuple[type, type]:
    from .litellm import LiteLLM, LiteLLMOptions

    return LiteLLM, LiteLLMOptions


def _start_litellm_import() -> None:
    global _litellm_future  # noqa: PLW0603
    with _import_lock:
        if _litellm_future is None:
            _litellm_future = _import_executor.submit(_import_litellm)


def __getattr__(name: str) -> type:
    if name in ("LiteLLM", "LiteLLMOptions"):
        _start_litellm_import()
        LiteLLM, LiteLLMOptions = _litellm_future.result()

        if name == "LiteLLM":
            return LiteLLM
        elif name == "LiteLLMOptions":
            return LiteLLMOptions

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Dynamic __all__ to handle lazy-loaded LiteLLM imports
__all__ = ["LLM", "LocalLLM", "LocalLLMOptions", "ToolCall", "Usage"]


def __dir__() -> list[str]:
    """Return available module attributes including lazy-loaded ones."""
    return __all__ + ["LiteLLM", "LiteLLMOptions"]
