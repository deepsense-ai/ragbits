"""
Type definitions for the hooks system.

This module contains all type definitions including EventType and callback
types for the hooks system.
"""

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Union

from ragbits.agents.tool import ToolCallResult, ToolReturn
from ragbits.core.llms.base import ToolCall

if TYPE_CHECKING:
    from ragbits.agents._main import AgentOptions, AgentResult, AgentRunContext


class EventType(str, Enum):
    """
    Types of events that can be hooked.

    Attributes:
        PRE_TOOL: Triggered before a tool is invoked
        POST_TOOL: Triggered after a tool completes
        PRE_RUN: Triggered before the agent run starts
        POST_RUN: Triggered after the agent run completes
        ON_EVENT: Triggered for each streaming event (str, ToolCall, ToolCallResult)
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_RUN = "pre_run"
    POST_RUN = "post_run"
    ON_EVENT = "on_event"


PreToolCallback = Callable[[ToolCall], Awaitable[ToolCall]]
PostToolCallback = Callable[[ToolCall, ToolReturn], Awaitable[ToolReturn]]
PreRunCallback = Callable[[Any, "AgentOptions", "AgentRunContext"], Awaitable[Any]]
PostRunCallback = Callable[["AgentResult", "AgentOptions", "AgentRunContext"], Awaitable["AgentResult"]]
OnEventCallback = Callable[
    [Union[str, ToolCall, ToolCallResult], str],
    Awaitable[Union[str, ToolCall, ToolCallResult, None]],
]

HookCallback = Union[PreToolCallback, PostToolCallback, PreRunCallback, PostRunCallback, OnEventCallback]
