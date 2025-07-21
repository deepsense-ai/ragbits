from __future__ import annotations

__all__ = ["ChatClientRequestError", "ChatClientResponseError"]


class ChatClientRequestError(Exception):
    """Raised when an HTTP request fails."""


class ChatClientResponseError(Exception):
    """Raised when an HTTP response is invalid."""
