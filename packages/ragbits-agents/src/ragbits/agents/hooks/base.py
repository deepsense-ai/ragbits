"""
Base classes for the hooks system.
"""

from typing import Generic, TypeVar

from ragbits.agents.hooks.types import EventType

CallbackT = TypeVar("CallbackT")


class Hook(Generic[CallbackT]):
    """
    A hook that intercepts execution at various lifecycle points.

    Hooks allow you to:
    - Validate inputs before execution (pre hooks)
    - Control access (pre hooks)
    - Modify inputs (pre hooks)
    - Deny execution (pre hooks)
    - Modify outputs (post hooks)
    - Handle errors (post hooks)

    Attributes:
        event_type: The type of event (e.g., PRE_TOOL, POST_TOOL)
        callback: The async function to call when the event is triggered
        tool_names: List of tool names this hook applies to. If None, applies to all tools.
        priority: Execution priority (lower numbers execute first, default: 100)

    Example:
        ```python
        from ragbits.agents.hooks import Hook, EventType
        from ragbits.core.llms.base import ToolCall


        async def validate_input(tool_call: ToolCall) -> ToolCall:
            if tool_call.name == "dangerous_tool":
                return tool_call.model_copy(update={"decision": "deny", "reason": "Not allowed"})
            return tool_call


        hook = Hook(event_type=EventType.PRE_TOOL, callback=validate_input, tool_names=["dangerous_tool"], priority=10)
        ```
    """

    def __init__(
        self,
        event_type: EventType,
        callback: CallbackT,
        tool_names: list[str] | None = None,
        priority: int = 100,
    ) -> None:
        """
        Initialize a hook.

        Args:
            event_type: The type of event (e.g., PRE_TOOL, POST_TOOL)
            callback: The async function to call when the event is triggered
            tool_names: List of tool names this hook applies to. If None, applies to all tools.
            priority: Execution priority (lower numbers execute first, default: 100)
        """
        self.event_type = event_type
        self.callback: CallbackT = callback
        self.tool_names = tool_names
        self.priority = priority

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
