"""
Type definitions for the hooks system.

This module contains all type definitions including EventType, callback types,
input types, and output types for the hooks system.
"""

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator

from ragbits.agents.confirmation import ConfirmationRequest
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


class HookEventIO(BaseModel):
    """
    Base class for hook inputs and outputs.

    Contains the common event_type attribute shared by all hook events.

    Attributes:
        event_type: The type of event
    """

    model_config = {"arbitrary_types_allowed": True}

    event_type: EventType


class PreToolInput(HookEventIO):
    """
    Input passed to pre-tool hook callbacks.

    This is provided before a tool is invoked, allowing hooks to:
    - Inspect the tool call
    - Modify tool arguments
    - Deny execution

    Attributes:
        event_type: Always EventType.PRE_TOOL (unchangeable)
        tool_call: The complete tool call (contains name, arguments, id, type)
    """

    event_type: Literal[EventType.PRE_TOOL] = Field(default=EventType.PRE_TOOL, frozen=True)
    tool_call: ToolCall


class PostToolInput(HookEventIO):
    """
    Input passed to post-tool hook callbacks.

    This is provided after a tool completes, allowing hooks to:
    - Inspect the tool result
    - Modify tool output
    - Handle errors

    Attributes:
        event_type: Always EventType.POST_TOOL (unchangeable)
        tool_call: The original tool call
        output: The result returned by the tool (None if error occurred)
        error: Any error that occurred during execution (None if successful)
    """

    event_type: Literal[EventType.POST_TOOL] = Field(default=EventType.POST_TOOL, frozen=True)
    tool_call: ToolCall
    output: Any = None
    error: Exception | None = None


class PreToolOutput(HookEventIO):
    """
    Output returned by pre-tool hook callbacks.

    This allows hooks to control tool execution. The output always contains
    arguments (either original or modified).

    Attributes:
        event_type: Always EventType.PRE_TOOL (unchangeable)
        arguments: Tool arguments to use (original or modified) - always present
        decision: The decision on tool execution ("pass", "ask", "deny")
        reason: Explanation for ask/deny decisions (required for "ask" and "deny", can be None for "pass")
        confirmation_request: Full confirmation request when decision is "ask" (set by HookManager)
    """

    event_type: Literal[EventType.PRE_TOOL] = Field(default=EventType.PRE_TOOL, frozen=True)  # type: ignore[assignment]
    arguments: dict[str, Any]
    decision: Literal["pass", "ask", "deny"] = "pass"
    reason: str | None = None
    confirmation_request: ConfirmationRequest | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "PreToolOutput":
        """Validate that reason is provided for ask and deny decisions."""
        if self.decision in ("ask", "deny") and not self.reason:
            raise ValueError(f"reason is required when decision='{self.decision}'")
        return self


class PostToolOutput(HookEventIO):
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


# Type aliases for hook callbacks
PreToolHookCallback: TypeAlias = Callable[["PreToolInput"], Awaitable["PreToolOutput"]]
PostToolHookCallback: TypeAlias = Callable[["PostToolInput"], Awaitable["PostToolOutput"]]
