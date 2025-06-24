from __future__ import annotations

from collections.abc import Generator
from typing import Any

import httpx

from ..interface.types import ChatResponse
from .base import SyncChatClientBase, SyncConversationBase
from .conversation import Conversation

__all__ = ["RagbitsChatClient"]

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class RagbitsChatClient(SyncChatClientBase):
    """Stateless *synchronous* Ragbits chat client.

    The sole responsibility of this class is to spawn new
    :class:`ragbits.chat.clients.conversation.Conversation` objects. All
    conversation-specific state (history, server-state, etc.) lives in the
    returned *Conversation* instance.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, headers=_DEFAULT_HEADERS)

    def new_conversation(self) -> SyncConversationBase:
        """Return a brand-new :class:`Conversation`."""
        return Conversation(base_url=self._base_url, http_client=self._client)

    def close(self) -> None:
        """Close the underlying *httpx.Client* session."""
        self._client.close()

    def ask(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Convenience wrapper that proxies through a fresh Conversation.

        This preserves the original *ask* method for backwards–compatibility
        while encouraging users to work with :pyclass:`Conversation` objects
        directly. Each invocation operates on a **new** conversation so no
        state is preserved across calls.
        """
        conv = self.new_conversation()
        return conv.ask(message, context=context)

    def send_message(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Stateless proxy to :pyclass:`Conversation.send_message`."""
        conv = self.new_conversation()
        yield from conv.send_message(message, context=context)
