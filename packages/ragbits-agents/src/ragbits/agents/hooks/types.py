"""
Type definitions for the hooks system.

This module contains all type definitions including EventType and callback Protocol
types for the hooks system.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, Union, runtime_checkable

from ragbits.agents.tool import ToolReturn
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
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_RUN = "pre_run"
    POST_RUN = "post_run"


@runtime_checkable
class PreToolCallback(Protocol):
    """Protocol for pre-tool hook callbacks.

    Receives a ToolCall and returns a (potentially modified) ToolCall.
    Set decision/reason on the returned ToolCall to control execution.
    """

    async def __call__(self, tool_call: ToolCall) -> ToolCall: ...


@runtime_checkable
class PostToolCallback(Protocol):
    """Protocol for post-tool hook callbacks.

    Receives the original ToolCall and the ToolReturn, returns a (potentially modified) ToolReturn.
    """

    async def __call__(self, tool_call: ToolCall, tool_return: ToolReturn) -> ToolReturn: ...


@runtime_checkable
class PreRunCallback(Protocol):
    """Protocol for pre-run hook callbacks.

    Receives the agent input, options, and context. Returns the (potentially modified) input.
    """

    async def __call__(
        self,
        input: Any,
        options: "AgentOptions | None",
        context: "AgentRunContext | None",
    ) -> Any: ...


@runtime_checkable
class PostRunCallback(Protocol):
    """Protocol for post-run hook callbacks.

    Receives the agent result, options, and context. Returns the (potentially modified) result.
    """

    async def __call__(
        self,
        result: "AgentResult",
        options: "AgentOptions | None",
        context: "AgentRunContext | None",
    ) -> "AgentResult": ...


HookCallback = Union[PreToolCallback, PostToolCallback, PreRunCallback, PostRunCallback]
