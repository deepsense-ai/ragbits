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
    tool_name: str
    """Name of the tool requiring confirmation."""
    tool_description: str
    """Description of what the tool does."""
    arguments: dict[str, Any]
    """Arguments that will be passed to the tool."""
