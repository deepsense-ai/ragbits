from __future__ import annotations


class ChatClientError(Exception):
    """Base class for all chat client related exceptions."""


class ChatClientRequestError(ChatClientError):
    """Raised when an error occurs while making a request to the server."""


class ChatClientResponseError(ChatClientError):
    """Raised when the server responds with an unexpected status code."""
