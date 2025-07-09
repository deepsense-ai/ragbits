from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from types import TracebackType
from typing import Any

import httpx

from ..interface.types import ChatResponse
from .conversation import RagbitsConversation, SyncRagbitsConversation

__all__ = ["RagbitsChatClient", "SyncRagbitsChatClient"]

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class RagbitsChatClient:
    """Stateless **asynchronous** Ragbits chat client."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout, headers=_DEFAULT_HEADERS)

    def new_conversation(self) -> RagbitsConversation:
        """Return a brand-new RagbitsConversation."""
        return RagbitsConversation(base_url=self._base_url, http_client=self._client)

    async def aclose(self) -> None:
        """Close the underlying *httpx.AsyncClient* session."""
        await self._client.aclose()

    async def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ChatResponse]:
        """Send *message* and return **all** response chunks."""
        conv = self.new_conversation()
        return await conv.run(message, context=context)

    async def run_streaming(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""
        conv = self.new_conversation()
        async for chunk in conv.run_streaming(message, context=context):
            yield chunk

    async def __aenter__(self) -> RagbitsChatClient:
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


class SyncRagbitsChatClient:
    """Stateless *synchronous* Ragbits chat client.

    The sole responsibility of this class is to spawn new
    SyncRagbitsConversation objects. All
    conversation-specific state (history, server-state, etc.) lives in the
    returned *SyncRagbitsConversation* instance.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, headers=_DEFAULT_HEADERS)

    def new_conversation(self) -> SyncRagbitsConversation:
        """Return a brand-new SyncRagbitsConversation."""
        return SyncRagbitsConversation(base_url=self._base_url, http_client=self._client)

    def close(self) -> None:
        """Close the underlying *httpx.Client* session."""
        self._client.close()

    def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ChatResponse]:
        """Send *message* and return **all** response chunks."""
        conv = self.new_conversation()
        return conv.run(message, context=context)

    def run_streaming(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""
        conv = self.new_conversation()
        yield from conv.run_streaming(message, context=context)

    def __enter__(self) -> SyncRagbitsChatClient:
        """Return *self* to allow usage via the *with* statement."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Ensure the underlying HTTP session is closed on context exit."""
        self.close()
