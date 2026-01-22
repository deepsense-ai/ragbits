"""
Type definitions for the hooks system.

This module contains all type definitions including EventType, callback types,
input types, and output types for the hooks system.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from ragbits.agents._main import AgentRunContext
    from ragbits.core.llms.base import ToolCall


class EventType(str, Enum):
    """
    Types of events that can be hooked.

    Attributes:
        PRE_TOOL: Triggered before a tool is invoked
        POST_TOOL: Triggered after a tool completes
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"


class HookInput(BaseModel):
    """
    Base input for all hook callbacks.

    Contains common attributes shared by all hook types.

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
    - Modify tool arguments
    - Deny execution

    Attributes:
        event_type: Always EventType.PRE_TOOL (unchangeable)
        context: The agent run context
        tool_call: The complete tool call (contains name, arguments, id, type)
    """

    event_type: Literal[EventType.PRE_TOOL] = Field(default=EventType.PRE_TOOL, frozen=True)
    tool_call: ToolCall


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
        tool_call: The original tool call
        output: The result returned by the tool (None if error occurred)
        error: Any error that occurred during execution (None if successful)
    """

    event_type: Literal[EventType.POST_TOOL] = Field(default=EventType.POST_TOOL, frozen=True)
    tool_call: ToolCall
    output: Any = None
    error: Exception | None = None


class HookOutput(BaseModel):
    """
    Base output for all hook callbacks.

    Contains common attributes shared by all hook output types.

    Attributes:
        event_type: The type of event
    """

    event_type: EventType


class PreToolOutput(HookOutput):
    """
    Output returned by pre-tool hook callbacks.

    This allows hooks to control tool execution. The output always contains
    arguments (either original or modified).

    Attributes:
        event_type: Always EventType.PRE_TOOL (unchangeable)
        arguments: Tool arguments to use (original or modified) - always present
        decision: The decision on tool execution ("pass", "ask", "deny")
        reason: Explanation for ask/deny decisions (required for "ask" and "deny", can be None for "pass")
    """

    event_type: Literal[EventType.PRE_TOOL] = Field(default=EventType.PRE_TOOL, frozen=True)  # type: ignore[assignment]
    arguments: dict[str, Any]
    decision: Literal["pass", "ask", "deny"] = "pass"
    reason: str | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "PreToolOutput":
        """Validate that reason is provided for ask and deny decisions."""
        if self.decision in ("ask", "deny") and not self.reason:
            raise ValueError(f"reason is required when decision='{self.decision}'")
        return self


class PostToolOutput(HookOutput):
    """
    Output returned by post-tool hook callbacks.

    The output always contains the tool output (either original or modified).

    Attributes:
        event_type: Always EventType.POST_TOOL (unchangeable)
        output: Tool output to use (original or modified) - always present

    Example:
        ```python
        # Pass through unchanged
        return PostToolOutput(output=input.output)

        # Modify output
        return PostToolOutput(output={"filtered": data})
        ```
    """

    event_type: Literal[EventType.POST_TOOL] = Field(default=EventType.POST_TOOL, frozen=True)  # type: ignore[assignment]
    output: Any


PreToolCallback = Callable[[PreToolInput], Awaitable[PreToolOutput | None]]
PostToolCallback = Callable[[PostToolInput], Awaitable[PostToolOutput | None]]

HookCallback = PreToolCallback | PostToolCallback
