"""
Type definitions for the hooks system.

This module contains all type definitions including EventType and callback
types for the hooks system.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable
from enum import Enum
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Union

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import ToolCallResult, ToolEvent, ToolReturn
from ragbits.core.llms.base import ToolCall, Usage
from ragbits.core.prompt.base import BasePrompt

if TYPE_CHECKING:
    from ragbits.agents._main import AgentOptions, AgentResult, AgentRunContext, DownstreamAgentResult


StreamingEvent = Union[
    str,
    ToolCall,
    ToolCallResult,
    ToolEvent,
    "DownstreamAgentResult",
    SimpleNamespace,
    BasePrompt,
    Usage,
    ConfirmationRequest,
]


class EventType(str, Enum):
    """
    Types of events that can be hooked.

    Attributes:
        PRE_TOOL: Triggered before a tool is invoked
        POST_TOOL: Triggered after a tool completes
        PRE_RUN: Triggered before the agent run starts
        POST_RUN: Triggered after the agent run completes
        ON_EVENT: Triggered for each streaming event
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_RUN = "pre_run"
    POST_RUN = "post_run"
    ON_EVENT = "on_event"


PreToolCallback = Callable[[ToolCall], Awaitable[ToolCall]]
PostToolCallback = Callable[[ToolCall, ToolReturn], Awaitable[ToolReturn]]
PreRunCallback = Callable[[Any, "AgentOptions[Any]", "AgentRunContext"], Awaitable[Any]]
PostRunCallback = Callable[["AgentResult[Any]", "AgentOptions[Any]", "AgentRunContext"], Awaitable["AgentResult[Any]"]]
OnEventCallback = Callable[[StreamingEvent], Awaitable[StreamingEvent | None] | AsyncGenerator[StreamingEvent, None]]

HookCallback = PreToolCallback | PostToolCallback | PreRunCallback | PostRunCallback | OnEventCallback
