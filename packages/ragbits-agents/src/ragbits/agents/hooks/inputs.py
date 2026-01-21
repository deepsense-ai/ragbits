"""
Input types for hook callbacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from ragbits.agents._main import AgentRunContext


class BaseInput(BaseModel):
    """
    Base input for all hook callbacks.

    Attributes:
        context: The agent run context providing access to runtime state
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context: AgentRunContext


class PreToolInput(BaseInput):
    """
    Input passed to pre-tool hook callbacks.

    This is provided before a tool is invoked, allowing hooks to:
    - Inspect the tool call
    - Modify tool input
    - Deny execution

    Attributes:
        tool_use_id: Unique identifier for this tool invocation
        tool_name: Name of the tool being invoked
        tool_input: Arguments being passed to the tool
        context: The agent run context
    """

    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]


class PostToolInput(BaseInput):
    """
    Input passed to post-tool hook callbacks.

    This is provided after a tool completes, allowing hooks to:
    - Inspect the tool result
    - Modify tool output
    - Handle errors

    Attributes:
        tool_use_id: Unique identifier for this tool invocation
        tool_name: Name of the tool that was invoked
        tool_input: Arguments that were passed to the tool
        tool_output: The result returned by the tool (None if error occurred)
        error: Any error that occurred during execution (None if successful)
        context: The agent run context
    """

    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Any = None
    error: Exception | None = None
