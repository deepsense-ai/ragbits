"""
Helper functions for creating common hooks.

This module provides factory functions for creating commonly used hooks.
"""

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import EventType, PreToolInput, PreToolOutput


def create_confirmation_hook(
    tool_names: list[str] | None = None, priority: int = 1
) -> Hook[PreToolInput, PreToolOutput]:
    """
    Create a hook that requires user confirmation before tool execution.

    The hook returns "ask" decision, which causes the agent to yield a ConfirmationRequest
    and wait for user approval/decline.

    Args:
        tool_names: List of tool names to require confirmation for. If None, applies to all tools.
        priority: Hook priority (default: 1, runs first)

    Returns:
        Hook configured to require confirmation

    Example:
        ```python
        from ragbits.agents import Agent
        from ragbits.agents.hooks.confirmation import create_confirmation_hook

        agent = Agent(
            tools=[delete_file, send_email], hooks=[create_confirmation_hook(tool_names=["delete_file", "send_email"])]
        )
        ```
    """

    async def confirm_hook(input_data: PreToolInput) -> PreToolOutput:
        """Hook that always returns 'ask' to require confirmation."""
        return PreToolOutput(
            arguments=input_data.tool_call.arguments,
            decision="ask",
            reason=f"Tool '{input_data.tool_call.name}' requires user confirmation",
        )

    return Hook(
        event_type=EventType.PRE_TOOL,
        callback=confirm_hook,
        tool_names=tool_names,
        priority=priority,
    )
