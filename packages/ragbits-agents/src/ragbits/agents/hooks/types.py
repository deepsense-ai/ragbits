"""
Type definitions for the hooks system.

This module contains all type definitions including EventType, callback types,
input types, and output types for the hooks system.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypeAlias

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import ToolReturn
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


@dataclass
class PreToolInput:
    """
    Input passed to pre-tool hook callbacks.

    Attributes:
        tool_call: The complete tool call (contains name, arguments, id, type)
        event_type: Always EventType.PRE_TOOL
    """

    tool_call: ToolCall
    event_type: Literal[EventType.PRE_TOOL] = EventType.PRE_TOOL


@dataclass
class PostToolInput:
    """
    Input passed to post-tool hook callbacks.

    Attributes:
        tool_call: The original tool call
        tool_return: The result returned by the tool
        event_type: Always EventType.POST_TOOL
    """

    tool_call: ToolCall
    tool_return: ToolReturn
    event_type: Literal[EventType.POST_TOOL] = EventType.POST_TOOL


@dataclass
class PreToolOutput:
    """
    Output returned by pre-tool hook callbacks.

    Attributes:
        arguments: Tool arguments to use (original or modified)
        decision: The decision on tool execution ("pass", "ask", "deny")
        reason: Explanation for ask/deny decisions
        confirmation_request: Full confirmation request when decision is "ask"
        event_type: Always EventType.PRE_TOOL
    """

    arguments: dict[str, Any]
    decision: Literal["pass", "ask", "deny"] = "pass"
    reason: str | None = None
    confirmation_request: ConfirmationRequest | None = None
    event_type: Literal[EventType.PRE_TOOL] = EventType.PRE_TOOL

    def __post_init__(self) -> None:
        """Validate that reason is provided for ask and deny decisions."""
        if self.decision in ("ask", "deny") and not self.reason:
            raise ValueError(f"reason is required when decision='{self.decision}'")


@dataclass
class PostToolOutput:
    """
    Output returned by post-tool hook callbacks.

    Attributes:
        tool_return: Tool output to use (original or modified)
        event_type: Always EventType.POST_TOOL (unchangeable)
    """

    tool_return: ToolReturn
    event_type: Literal[EventType.POST_TOOL] = EventType.POST_TOOL


# Type aliases for hook callbacks
PreToolHookCallback: TypeAlias = Callable[["PreToolInput"], Awaitable["PreToolOutput"]]
PostToolHookCallback: TypeAlias = Callable[["PostToolInput"], Awaitable["PostToolOutput"]]
