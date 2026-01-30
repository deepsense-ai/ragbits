"""
Base classes for the hooks system.
"""

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from ragbits.agents.hooks.types import EventType, HookEventIO

HookInputT = TypeVar("HookInputT", bound=HookEventIO)
HookOutputT = TypeVar("HookOutputT", bound=HookEventIO)


class Hook(Generic[HookInputT, HookOutputT]):
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
        from ragbits.agents.hooks import Hook, EventType, PreToolInput, PreToolOutput


        async def validate_input(input_data: PreToolInput) -> PreToolOutput:
            if input_data.tool_call.name == "dangerous_tool":
                return PreToolOutput(arguments=input_data.tool_call.arguments, decision="deny", reason="Not allowed")
            return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")


        hook: Hook[PreToolInput, PreToolOutput] = Hook(
            event_type=EventType.PRE_TOOL, callback=validate_input, tool_names=["dangerous_tool"], priority=10
        )
        ```
    """

    def __init__(
        self,
        event_type: EventType,
        callback: Callable[[HookInputT], Awaitable[HookOutputT]],
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
        self.callback = callback
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

    async def execute(self, hook_input: HookInputT) -> HookOutputT:
        """
        Execute the hook callback with the given input.

        Args:
            hook_input: The input to pass to the callback

        Returns:
            The output from the callback
        """
        return await self.callback(hook_input)
