from __future__ import annotations

from collections.abc import AsyncGenerator
from types import TracebackType
from typing import Any

import httpx

from ..base import AsyncChatClientBase, AsyncConversationBase
from ..conversation import AsyncConversation

__all__ = ["AsyncRagbitsChatClient"]

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class AsyncRagbitsChatClient(AsyncChatClientBase):
    """Stateless **asynchronous** Ragbits chat client."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout, headers=_DEFAULT_HEADERS)

    def new_conversation(self) -> AsyncConversationBase:
        """Return a brand-new :class:`AsyncConversation`."""
        return AsyncConversation(base_url=self._base_url, http_client=self._client)

    async def aclose(self) -> None:
        """Close the underlying *httpx.AsyncClient* session."""
        await self._client.aclose()

    async def ask(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Convenience wrapper that proxies through a fresh AsyncConversation."""
        conv = self.new_conversation()
        return await conv.ask(message, context=context)

    async def send_message(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Any, None]:
        """Stateless proxy to :class:`AsyncConversation.send_message`."""
        conv = self.new_conversation()
        async for chunk in conv.send_message(message, context=context):
            yield chunk

    async def __aenter__(self) -> AsyncRagbitsChatClient:
        """Return *self* inside an ``async with`` block."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Ensure the underlying async HTTP session is closed on exit."""
        await self.aclose()
