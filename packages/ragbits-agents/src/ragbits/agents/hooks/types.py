"""
Type definitions for the hooks system.

This module contains all type definitions including EventType, callback types,
input types, and output types for the hooks system.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from ragbits.agents._main import AgentRunContext


# ============================================================================
# Event Types
# ============================================================================


class EventType(str, Enum):
    """
    Types of events that can be hooked.

    Attributes:
        PRE_TOOL: Triggered before a tool is invoked
        POST_TOOL: Triggered after a tool completes
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"


# ============================================================================
# Input Types
# ============================================================================


class HookInput(BaseModel):
    """
    Base input for all hook callbacks.

    Contains common attributes shared by all hook types (tool, run, etc.).

    Attributes:
        event_type: The type of event
        context: The agent run context providing access to runtime state
    """

    event_type: EventType
    context: AgentRunContext


class PreToolInput(HookInput):
    """
    Input passed to pre-tool hook callbacks.

    This is provided before a tool is invoked, allowing hooks to:
    - Inspect the tool call
    - Modify tool input
    - Deny execution

    Attributes:
        event_type: Always EventType.PRE_TOOL (unchangeable)
        context: The agent run context
        tool_use_id: Unique identifier for this tool invocation
        tool_name: Name of the tool being invoked
        tool_input: Arguments being passed to the tool
    """

    event_type: Literal[EventType.PRE_TOOL] = Field(default=EventType.PRE_TOOL, frozen=True)
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]


class PostToolInput(HookInput):
    """
    Input passed to post-tool hook callbacks.

    This is provided after a tool completes, allowing hooks to:
    - Inspect the tool result
    - Modify tool output
    - Handle errors

    Attributes:
        event_type: Always EventType.POST_TOOL (unchangeable)
        context: The agent run context
        tool_use_id: Unique identifier for this tool invocation
        tool_name: Name of the tool that was invoked
        tool_input: Arguments that were passed to the tool
        tool_output: The result returned by the tool (None if error occurred)
        error: Any error that occurred during execution (None if successful)
    """

    event_type: Literal[EventType.POST_TOOL] = Field(default=EventType.POST_TOOL, frozen=True)
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Any = None
    error: Exception | None = None


# ============================================================================
# Output Types
# ============================================================================


class HookOutput(BaseModel):
    """
    Base output for all hook callbacks.

    Contains common attributes shared by all hook output types.

    Attributes:
        event_type: The type of event
        result: The result data (type varies by hook type)
    """

    event_type: EventType
    result: Any = None


class PreToolOutput(HookOutput):
    """
    Output returned by pre-tool hook callbacks.

    This allows hooks to control tool execution:
    - "allow": Proceed with tool execution (default behavior)
    - "deny": Block tool execution and provide a reason
    - "modify": Execute tool with modified input

    Attributes:
        event_type: Always EventType.PRE_TOOL (unchangeable)
        action: The action to take ("allow", "deny", or "modify")
        result: Modified tool input (required when action="modify") or denial message (required when action="deny")
    """

    event_type: Literal[EventType.PRE_TOOL] = Field(default=EventType.PRE_TOOL, frozen=True)  # type: ignore[assignment]
    action: Literal["allow", "deny", "modify"]
    result: dict[str, Any] | str | None = None  # type: ignore[assignment]

    @model_validator(mode="after")
    def validate_action_result(self) -> "PreToolOutput":
        """Validate that result is provided and has correct type for each action."""
        if self.action == "modify":
            if self.result is None:
                raise ValueError("result must be provided when action='modify'")
            if not isinstance(self.result, dict):
                raise ValueError("result must be a dict when action='modify'")
        elif self.action == "deny":
            if self.result is None:
                raise ValueError("result must be provided when action='deny'")
            if not isinstance(self.result, str):
                raise ValueError("result must be a string (denial message) when action='deny'")
        return self


class PostToolOutput(HookOutput):
    """
    Output returned by post-tool hook callbacks.

    This allows hooks to modify tool results:
    - "pass": Return the original tool output unchanged
    - "modify": Return modified tool output

    Attributes:
        event_type: Always EventType.POST_TOOL (unchangeable)
        action: The action to take ("pass" or "modify")
        result: Modified tool output (required when action="modify")
    """

    event_type: Literal[EventType.POST_TOOL] = Field(default=EventType.POST_TOOL, frozen=True)  # type: ignore[assignment]
    action: Literal["pass", "modify"]

    @model_validator(mode="after")
    def validate_action_result(self) -> "PostToolOutput":
        """Validate that result is provided when action='modify'."""
        if self.action == "modify" and self.result is None:
            raise ValueError("result must be provided when action='modify'")
        return self


# ============================================================================
# Callback Types
# ============================================================================

# Type aliases for hook callbacks
PreToolCallback = Callable[[PreToolInput], Awaitable[PreToolOutput | None]]
PostToolCallback = Callable[[PostToolInput], Awaitable[PostToolOutput | None]]

# Union of all callback types
HookCallback = PreToolCallback | PostToolCallback
