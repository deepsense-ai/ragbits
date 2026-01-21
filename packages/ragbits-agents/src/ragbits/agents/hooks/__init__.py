"""
Hooks system for tool lifecycle events.

This module provides a comprehensive hook system that allows users to register
custom logic at various points in the tool execution lifecycle.

Available event types:
- PRE_TOOL: Before a tool is invoked
- POST_TOOL: After a tool completes

Example usage:

    from ragbits.agents.hooks import (
        EventType,
        ToolHook,
        PreToolInput,
        PreToolOutput,
        PostToolInput,
        PostToolOutput,
    )

    # Create a pre-tool hook
    async def validate_input(input_data: PreToolInput) -> PreToolOutput | None:
        if input_data.tool_name == "dangerous_tool":
            return PreToolOutput(
                action="deny",
                denial_message="This tool is not allowed"
            )
        return None

    # Create hook instance
    hook = ToolHook(
        event_type=EventType.PRE_TOOL,
        callback=validate_input,
        tool_names=["dangerous_tool"],
        priority=10,
        name="security_check"
    )

    # Register hooks with agent
    agent = Agent(
        ...,
        hooks=[hook]
    )
"""

from ragbits.agents.hooks.base import (
    EventType,
    ToolHook,
    PreToolCallback,
    PostToolCallback,
)
from ragbits.agents.hooks.inputs import (
    BaseInput,
    PreToolInput,
    PostToolInput,
)
from ragbits.agents.hooks.outputs import (
    PreToolOutput,
    PostToolOutput,
)
from ragbits.agents.hooks.manager import HookManager

__all__ = [
    # Event types and classes
    "EventType",
    "ToolHook",
    # Callback types
    "PreToolCallback",
    "PostToolCallback",
    # Input types
    "BaseInput",
    "PreToolInput",
    "PostToolInput",
    # Output types
    "PreToolOutput",
    "PostToolOutput",
    # Manager
    "HookManager",
]
