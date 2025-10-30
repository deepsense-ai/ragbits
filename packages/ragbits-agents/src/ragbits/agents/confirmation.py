"""
Tool confirmation functionality for agents.

This module provides the ability to request user confirmation before executing certain tools.
"""

import asyncio
import uuid
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
    timeout_seconds: int = 60
    """Timeout in seconds before auto-denying the request."""


class ConfirmationManager:
    """
    Manages pending tool confirmations.

    This manager tracks confirmation requests and their associated futures,
    allowing the agent to pause execution while waiting for user input.
    """

    def __init__(self) -> None:
        """Initialize the confirmation manager."""
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def request_confirmation(
        self,
        tool_name: str,
        tool_description: str,
        arguments: dict[str, Any],
        timeout_seconds: int = 60,
    ) -> tuple[ConfirmationRequest, asyncio.Future[bool]]:
        """
        Request confirmation for a tool execution.

        Args:
            tool_name: Name of the tool requiring confirmation.
            tool_description: Description of what the tool does.
            arguments: Arguments that will be passed to the tool.
            timeout_seconds: Timeout in seconds before auto-denying.

        Returns:
            Tuple of (confirmation_request, future that resolves to True/False).
        """
        confirmation_id = str(uuid.uuid4())
        future: asyncio.Future[bool] = asyncio.Future()

        self._pending[confirmation_id] = future

        # Set timeout
        asyncio.create_task(self._handle_timeout(confirmation_id, timeout_seconds))

        request = ConfirmationRequest(
            confirmation_id=confirmation_id,
            tool_name=tool_name,
            tool_description=tool_description,
            arguments=arguments,
            timeout_seconds=timeout_seconds,
        )

        return request, future

    async def _handle_timeout(self, confirmation_id: str, timeout_seconds: int) -> None:
        """
        Handle timeout for a confirmation request.

        Args:
            confirmation_id: ID of the confirmation request.
            timeout_seconds: Timeout duration in seconds.
        """
        await asyncio.sleep(timeout_seconds)

        if confirmation_id in self._pending:
            future = self._pending.pop(confirmation_id)
            if not future.done():
                future.set_result(False)  # Default to deny on timeout

    def resolve_confirmation(self, confirmation_id: str, confirmed: bool) -> bool:
        """
        Resolve a pending confirmation with the user's decision.

        Args:
            confirmation_id: ID of the confirmation request.
            confirmed: Whether the user confirmed (True) or denied (False).

        Returns:
            True if confirmation was found and resolved, False otherwise.
        """
        future = self._pending.pop(confirmation_id, None)
        if future and not future.done():
            future.set_result(confirmed)
            return True
        return False
