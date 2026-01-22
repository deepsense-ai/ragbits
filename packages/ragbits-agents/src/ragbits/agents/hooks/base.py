"""
Base classes for the hooks system.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ragbits.agents.hooks.types import EventType, HookCallback, HookInput, HookOutput


@dataclass
class Hook:
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
        tools: List of tool names this hook applies to. If None, applies to all tools.
        priority: Execution priority (lower numbers execute first, default: 100)

    Example:
        ```python
        from ragbits.agents.hooks import Hook, EventType, PreToolInput, PreToolOutput


        async def validate_input(input_data: PreToolInput) -> PreToolOutput | None:
            if input_data.tool_call.name == "dangerous_tool":
                return PreToolOutput(
                    arguments=input_data.tool_call.arguments,
                    decision="deny",
                    reason="Not allowed"
                )
            return None


        hook = Hook(event_type=EventType.PRE_TOOL, callback=validate_input, tools=["dangerous_tool"], priority=10)
        ```
    """

    event_type: "EventType"
    callback: "HookCallback"
    tools: list[str] | None = None
    priority: int = 100

    def matches_tool(self, tool_name: str) -> bool:
        """
        Check if this hook applies to the given tool name.

        Args:
            tool_name: The name of the tool to check

        Returns:
            True if this hook should be executed for the given tool
        """
        if self.tools is None:
            return True
        return tool_name in self.tools

    async def execute(self, hook_input: "HookInput") -> "HookOutput | None":
        """
        Execute the hook callback with the given input.

        Args:
            hook_input: The input to pass to the callback

        Returns:
            The output from the callback, or None if no action needed
        """
        return await self.callback(hook_input)  # type: ignore
