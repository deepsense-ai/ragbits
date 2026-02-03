"""
Type definitions for the hooks system.

This module contains all type definitions including EventType, callback types,
input types, and output types for the hooks system.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeAlias

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.tool import ToolReturn
from ragbits.core.llms.base import LLMClientOptionsT, ToolCall
from ragbits.core.prompt.prompt import PromptInputT, PromptOutputT

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


@dataclass
class PreRunInput(Generic[LLMClientOptionsT, PromptInputT]):
    """
    Input passed to pre-run hook callbacks.

    Attributes:
        input: The input for the agent run
        options: The options for the agent run
        context: The context for the agent run
        event_type: Always EventType.PRE_RUN
    """

    input: str | PromptInputT | None = None
    options: "AgentOptions[LLMClientOptionsT] | None" = None
    context: "AgentRunContext | None" = None
    event_type: Literal[EventType.PRE_RUN] = EventType.PRE_RUN


@dataclass
class PreRunOutput(Generic[PromptInputT]):
    """
    Output returned by pre-run hook callbacks.

    Attributes:
        output: The input to use (original or modified)
        event_type: Always EventType.PRE_RUN
    """

    output: str | PromptInputT | None = None
    event_type: Literal[EventType.PRE_RUN] = EventType.PRE_RUN


@dataclass
class PostRunInput(Generic[LLMClientOptionsT, PromptOutputT]):
    """
    Input passed to post-run hook callbacks.

    Attributes:
        result: The result from the agent run (AgentResult)
        options: The options for the agent run
        context: The context for the agent run
        event_type: Always EventType.POST_RUN
    """

    result: "AgentResult[PromptOutputT]"
    options: "AgentOptions[LLMClientOptionsT] | None" = None
    context: "AgentRunContext | None" = None
    event_type: Literal[EventType.POST_RUN] = EventType.POST_RUN


@dataclass
class PostRunOutput(Generic[PromptOutputT]):
    """
    Output returned by post-run hook callbacks.

    Attributes:
        result: The result to use (original or modified AgentResult)
        rerun: If True, triggers a rerun of the agent
        correction_prompt: Optional correction prompt to guide the rerun (used as input for the next run)
        event_type: Always EventType.POST_RUN
    """

    result: "AgentResult[PromptOutputT]"
    rerun: bool = False
    correction_prompt: str | None = None
    event_type: Literal[EventType.POST_RUN] = EventType.POST_RUN


# Type aliases for hook callbacks
PreToolHookCallback: TypeAlias = Callable[["PreToolInput"], Awaitable["PreToolOutput"]]
PostToolHookCallback: TypeAlias = Callable[["PostToolInput"], Awaitable["PostToolOutput"]]
PreRunHookCallback: TypeAlias = Callable[["PreRunInput"], Awaitable["PreRunOutput"]]
PostRunHookCallback: TypeAlias = Callable[["PostRunInput"], Awaitable["PostRunOutput"]]
