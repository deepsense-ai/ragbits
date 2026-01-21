"""
Base classes for the hooks system.
"""

from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ragbits.agents.hooks.inputs import PreToolInput, PostToolInput
    from ragbits.agents.hooks.outputs import PreToolOutput, PostToolOutput


class EventType(str, Enum):
    """
    Types of tool events that can be hooked.

    Attributes:
        PRE_TOOL: Triggered before a tool is invoked
        POST_TOOL: Triggered after a tool completes
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"


# Type aliases for hook callbacks
PreToolCallback = Callable[["PreToolInput"], Awaitable["PreToolOutput | None"]]
PostToolCallback = Callable[["PostToolInput"], Awaitable["PostToolOutput | None"]]


@dataclass
class ToolHook:
    """
    A hook that intercepts tool execution.

    Tool hooks allow you to:
    - Validate tool inputs before execution (pre-tool)
    - Control tool access (pre-tool)
    - Modify tool inputs (pre-tool)
    - Deny tool execution (pre-tool)
    - Modify tool outputs (post-tool)
    - Handle tool errors (post-tool)

    Attributes:
        event_type: The type of event (PRE_TOOL or POST_TOOL)
        callback: The async function to call when the event is triggered
        tool_names: List of tool names this hook applies to. If None, applies to all tools.
        priority: Execution priority (lower numbers execute first, default: 100)
        name: Optional name for debugging and logging

    Example:
        ```python
        async def validate_input(input_data: PreToolInput) -> PreToolOutput | None:
            if input_data.tool_name == "dangerous_tool":
                return PreToolOutput(action="deny", denial_message="Not allowed")
            return None

        hook = ToolHook(
            event_type=EventType.PRE_TOOL,
            callback=validate_input,
            tool_names=["dangerous_tool"],
            priority=10,
            name="security_check"
        )
        ```
    """

    event_type: EventType
    callback: PreToolCallback | PostToolCallback
    tool_names: list[str] | None = None
    priority: int = 100
    name: str | None = None

    def __post_init__(self) -> None:
        """Validate hook configuration."""
        if self.priority < 0:
            raise ValueError("Hook priority must be non-negative")
        if self.event_type not in (EventType.PRE_TOOL, EventType.POST_TOOL):
            raise ValueError(f"event_type must be PRE_TOOL or POST_TOOL, got {self.event_type}")

    def matches_tool(self, tool_name: str) -> bool:
        """
        Check if this hook applies to the given tool name.

        Args:
            tool_name: The name of the tool to check

        Returns:
            True if this hook should be executed for the given tool
        """
        if self.tool_names is None:
            return True
        return tool_name in self.tool_names

    async def execute(self, hook_input: "PreToolInput | PostToolInput") -> "PreToolOutput | PostToolOutput | None":
        """
        Execute the hook callback with the given input.

        Args:
            hook_input: The input to pass to the callback

        Returns:
            The output from the callback, or None if no action needed
        """
        return await self.callback(hook_input)  # type: ignore

    def __repr__(self) -> str:
        """Return a string representation of the hook."""
        name = self.name or "unnamed"
        tools = self.tool_names if self.tool_names else "all"
        return f"ToolHook(name={name}, tools={tools}, type={self.event_type}, priority={self.priority})"
