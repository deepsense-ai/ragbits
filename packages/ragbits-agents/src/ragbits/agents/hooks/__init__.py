"""
Hooks system for lifecycle events.

This module provides a comprehensive hook system that allows users to register
custom logic at various points in the execution lifecycle.

Available event types:
- PRE_TOOL: Before a tool is invoked
- POST_TOOL: After a tool completes
- PRE_RUN: Before the agent run starts
- POST_RUN: After the agent run completes

Example usage:

    from ragbits.agents.hooks import (
        EventType,
        Hook,
        PreToolInput,
        PreToolOutput,
    )

    # Create a pre-tool hook callback
    async def validate_input(input_data: PreToolInput) -> PreToolOutput:
        if input_data.tool_call.name == "dangerous_tool":
            return PreToolOutput(
                arguments=input_data.tool_call.arguments,
                decision="deny",
                reason="This tool is not allowed"
            )
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    # Create hook instance with proper type annotation
    hook: Hook[PreToolInput, PreToolOutput] = Hook(
        event_type=EventType.PRE_TOOL,
        callback=validate_input,
        tool_names=["dangerous_tool"],
        priority=10
    )

    # Register hooks with agent
    agent = Agent(
        ...,
        hooks=[hook]
    )
"""

from ragbits.agents.hooks.base import Hook, HookInputT, HookOutputT
from ragbits.agents.hooks.confirmation import create_confirmation_hook
from ragbits.agents.hooks.manager import HookManager
from ragbits.agents.hooks.types import (
    EventType,
    PostRunHookCallback,
    PostRunInput,
    PostRunOutput,
    PostToolHookCallback,
    PostToolInput,
    PostToolOutput,
    PreRunHookCallback,
    PreRunInput,
    PreRunOutput,
    PreToolHookCallback,
    PreToolInput,
    PreToolOutput,
)

__all__ = [
    # Event types
    "EventType",
    # Core classes
    "Hook",
    # Type variables
    "HookInputT",
    "HookManager",
    "HookOutputT",
    # Callback type aliases
    "PostRunHookCallback",
    # Input/output types
    "PostRunInput",
    "PostRunOutput",
    "PostToolHookCallback",
    "PostToolInput",
    "PostToolOutput",
    "PreRunHookCallback",
    "PreRunInput",
    "PreRunOutput",
    "PreToolHookCallback",
    "PreToolInput",
    "PreToolOutput",
    # Hook factories
    "create_confirmation_hook",
]
