import builtins
import importlib
import sys
from collections.abc import Mapping, Sequence
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def test_importing_agent_does_not_import_openai_tools() -> None:
    for module_name in list(sys.modules):
        if module_name == "ragbits.agents" or module_name.startswith("ragbits.agents."):
            sys.modules.pop(module_name)

    importlib.import_module("ragbits.agents")

    assert "ragbits.agents.tools.openai" not in sys.modules


def test_openai_tools_raise_helpful_error_without_openai_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    openai_tools = importlib.import_module("ragbits.agents.tools.openai")
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(openai_tools, "AsyncOpenAI", None)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match=r"ragbits-agents\[openai\]"):
        openai_tools.OpenAITools("test_model", None, tool_param=MagicMock())
