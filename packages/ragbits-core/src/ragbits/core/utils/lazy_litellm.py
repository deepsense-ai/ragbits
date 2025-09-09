import importlib
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from types import ModuleType
from typing import Any


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
                    cls._litellm_future = cls._import_executor.submit(lambda: importlib.import_module("litellm"))
        return instance

    @classmethod
    def _get_litellm_module(cls) -> ModuleType:
        """Get the lazily loaded litellm module for class methods."""
        if cls._litellm_module is None:
            with cls._litellm_module_lock:
                if cls._litellm_module is None:
                    if cls._litellm_future is not None:
                        # Wait for background import to complete
                        cls._litellm_module = cls._litellm_future.result()
                    else:
                        # Fallback to synchronous import
                        cls._litellm_module = importlib.import_module("litellm")
        return cls._litellm_module

    @property
    def _litellm(self) -> ModuleType:
        """Get the lazily loaded litellm module for instance methods."""
        return self._get_litellm_module()
