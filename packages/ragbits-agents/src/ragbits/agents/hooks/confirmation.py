"""
Helper functions for creating common hooks.

This module provides factory functions for creating commonly used hooks.
"""

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import EventType, PreToolInput, PreToolOutput


def requires_confirmation_hook(tools: list[str] | None = None, priority: int = 1) -> Hook[PreToolInput, PreToolOutput]:
    """
    Create a hook that requires user confirmation before tool execution.

    This replaces the @requires_confirmation decorator with a hook-based approach.
    The hook returns "ask" decision, which causes the agent to yield a ConfirmationRequest
    and wait for user approval/decline.

    Args:
        tools: List of tool names to require confirmation for. If None, applies to all tools.
        priority: Hook priority (default: 1, runs first)

    Returns:
        Hook configured to require confirmation

    Example:
        ```python
        from ragbits.agents import Agent
        from ragbits.agents.hooks.helpers import requires_confirmation_hook

        agent = Agent(tools=[delete_file, send_email], hooks=[requires_confirmation_hook(tools=["delete_file", "send_email"])])
        ```
    """  # noqa: E501

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
        tools=tools,
        priority=priority,
    )
