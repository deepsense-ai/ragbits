from typing import TYPE_CHECKING

from ragbits.agents.tools.memory import LongTermMemory, MemoryEntry, create_memory_tools
from ragbits.agents.tools.planning import Plan, PlanningState, Task, TaskStatus, create_planning_tools

if TYPE_CHECKING:
    from ragbits.agents.tools.openai import get_code_interpreter_tool, get_image_generation_tool, get_web_search_tool

_LAZY: dict[str, str] = {
    "get_code_interpreter_tool": "ragbits.agents.tools.openai",
    "get_image_generation_tool": "ragbits.agents.tools.openai",
    "get_web_search_tool": "ragbits.agents.tools.openai",
}


def __getattr__(name: str) -> object:
    if name in _LAZY:
        import importlib

        module = importlib.import_module(_LAZY[name])
        obj = getattr(module, name)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'ragbits.agents.tools' has no attribute {name!r}")


__all__ = [
    "LongTermMemory",
    "MemoryEntry",
    "Plan",
    "PlanningState",
    "Task",
    "TaskStatus",
    "create_memory_tools",
    "create_planning_tools",
    "get_code_interpreter_tool",
    "get_image_generation_tool",
    "get_web_search_tool",
]
