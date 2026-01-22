"""
Hooks system for lifecycle events.

This module provides a comprehensive hook system that allows users to register
custom logic at various points in the execution lifecycle.

Available event types:
- PRE_TOOL: Before a tool is invoked
- POST_TOOL: After a tool completes

Example usage:

    from ragbits.agents.hooks import (
        EventType,
        Hook,
        PreToolInput,
        PreToolOutput,
        PostToolInput,
        PostToolOutput,
    )

    # Create a pre-tool hook
    async def validate_input(input_data: PreToolInput) -> PreToolOutput | None:
        if input_data.tool_call.name == "dangerous_tool":
            return PreToolOutput(
                arguments=input_data.tool_call.arguments,
                decision="deny",
                reason="This tool is not allowed"
            )
        return None

    # Create hook instance
    hook = Hook(
        event_type=EventType.PRE_TOOL,
        callback=validate_input,
        tools=["dangerous_tool"],
        priority=10
    )

    # Register hooks with agent
    agent = Agent(
        ...,
        hooks=[hook]
    )
"""

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.manager import HookManager
from ragbits.agents.hooks.types import (
    EventType,
    HookCallback,
    HookInput,
    HookOutput,
    PostToolCallback,
    PostToolInput,
    PostToolOutput,
    PreToolCallback,
    PreToolInput,
    PreToolOutput,
)

__all__ = [
    # Event types
    "EventType",
    # Core classes
    "Hook",
    # Callback types
    "HookCallback",
    # Input types
    "HookInput",
    "HookManager",
    # Output types
    "HookOutput",
    "PostToolCallback",
    "PostToolInput",
    "PostToolOutput",
    "PreToolCallback",
    "PreToolInput",
    "PreToolOutput",
]
