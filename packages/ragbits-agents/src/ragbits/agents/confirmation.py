"""
Tool confirmation functionality for agents.

This module provides the ability to request user confirmation before executing certain tools.
"""

from typing import Any

from pydantic import BaseModel


class ConfirmationRequest(BaseModel):
    """Represents a tool confirmation request sent to the user."""

    confirmation_id: str
    """Unique identifier for this confirmation request."""
    tool_call_id: str
    """Identifier of the originating ToolCall — threads the tool_use and tool_result messages
    when the chat layer resumes execution via Agent.execute_tool_directly."""
    tool_name: str
    """Name of the tool requiring confirmation."""
    tool_description: str
    """Description of what the tool does."""
    arguments: dict[str, Any]
    """Arguments that will be passed to the tool."""
