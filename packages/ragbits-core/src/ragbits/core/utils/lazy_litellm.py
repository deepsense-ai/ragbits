import importlib
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from types import ModuleType
from typing import Any

_MISSING_LITELLM_MESSAGE = (
    "LiteLLM is not installed. Install the optional extra to use LiteLLM-backed "
    "components: pip install ragbits-core[litellm]"
)


def _import_litellm() -> ModuleType:
    try:
        return importlib.import_module("litellm")
    except ImportError as exc:
        raise ImportError(_MISSING_LITELLM_MESSAGE) from exc


class LazyLiteLLM:
    """Mixin class for lazy loading of litellm module."""

    _litellm_module: ModuleType | None = None
    _litellm_import_lock = threading.Lock()
    _litellm_module_lock = threading.Lock()
    _import_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="litellm-import")
    _litellm_future: Future[ModuleType] | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "LazyLiteLLM":
        """Start background import of litellm when instance is created."""
        instance = super().__new__(cls)
        # Start the import in background thread if not already started
        if cls._litellm_future is None:
            with cls._litellm_import_lock:
                if cls._litellm_future is None:
                    cls._litellm_future = cls._import_executor.submit(_import_litellm)
        return instance

    @classmethod
    def _get_litellm_module(cls) -> ModuleType:
        """Get the lazily loaded litellm module for class methods.

        Raises:
            ImportError: If the optional ``litellm`` dependency is not installed.
        """
        if cls._litellm_module is None:
            with cls._litellm_module_lock:
                if cls._litellm_module is None:
                    if cls._litellm_future is not None:
                        cls._litellm_module = cls._litellm_future.result()
                    else:
                        cls._litellm_module = _import_litellm()
        return cls._litellm_module

    @property
    def _litellm(self) -> ModuleType:
        """Get the lazily loaded litellm module for instance methods."""
        return self._get_litellm_module()
