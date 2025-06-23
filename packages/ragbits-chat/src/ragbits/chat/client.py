from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any, Dict, List, Optional

import httpx

from ._utils import build_api_url, parse_sse_line
from .types import (
    ChatResponse,
    ChatResponseType,
    Message,
    MessageRole,
    ServerState,
    map_history_to_messages,
)

__all__ = [
    "AsyncRagbitsChatClient",
    "RagbitsChatClient",
]

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class RagbitsChatClient:
    """Synchronous Ragbits chat client."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, headers=_DEFAULT_HEADERS)

        self.history: list[Message] = []
        self.conversation_id: str | None = None
        self.server_state: ServerState | None = None

        self._streaming_response: httpx.Response | None = None


    def new_conversation(self) -> None:
        """Reset local state – start fresh conversation."""
        self.history.clear()
        self.conversation_id = None
        self.server_state = None

    def ask(self, message: str, *, context: Dict[str, Any] | None = None) -> str:
        """Convenience wrapper around :py:meth:`send_message`.

        Collects the streaming response and returns the final assistant text.
        """
        assistant_reply_parts: List[str] = []
        for chunk in self.send_message(message, context=context):
            if chunk.type is ChatResponseType.TEXT:
                assistant_reply_parts.append(chunk.content)
        return "".join(assistant_reply_parts)

    def send_message(
        self,
        message: str,
        *,
        context: Dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Send *message* to server and *yield* :class:`ChatResponse` chunks.

        The generator can be cancelled at any time by simply breaking the
        iteration. Use :py:meth:`stop` to explicitly close the underlying
        HTTP connection if needed.
        """
        user_msg = Message(role=MessageRole.USER, content=message)
        self.history.append(user_msg)

        assistant_reply = Message(role=MessageRole.ASSISTANT, content="")
        self.history.append(assistant_reply)
        assistant_index = len(self.history) - 1

        merged_context: Dict[str, Any] = {}
        if self.server_state is not None:
            merged_context.update(self.server_state.model_dump())
        if self.conversation_id is not None:
            merged_context["conversation_id"] = self.conversation_id
        if context:
            merged_context.update(context)

        payload: Dict[str, Any] = {
            "message": message,
            "history": [m.model_dump() for m in map_history_to_messages(self.history)],
            "context": merged_context,
        }

        url = build_api_url(self._base_url, "/api/chat")

        with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            self._streaming_response = resp

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                parsed = parse_sse_line(raw_line)
                if parsed is None:
                    continue

                self._process_incoming(parsed, assistant_index)

                yield parsed

        self._streaming_response = None

    def stop(self) -> None:
        """Abort currently running stream (if any)."""
        if self._streaming_response is not None and not self._streaming_response.is_closed:
            self._streaming_response.close()
            self._streaming_response = None

    def _process_incoming(self, resp: ChatResponse, assistant_index: int) -> None:
        """Update local client-side state based on *resp*."""

        if resp.type is ChatResponseType.STATE_UPDATE:
            self.server_state = resp.content  # type: ignore[assignment]
        elif resp.type is ChatResponseType.CONVERSATION_ID:
            self.conversation_id = resp.content  # type: ignore[assignment]
        elif resp.type is ChatResponseType.MESSAGE_ID:
            pass
        elif resp.type is ChatResponseType.TEXT:
            assistant_msg = self.history[assistant_index]
            if isinstance(resp.content, str):
                assistant_msg.content += resp.content
        elif resp.type is ChatResponseType.REFERENCE:
            pass


class AsyncRagbitsChatClient:
    """Asynchronous Ragbits chat client (uses *httpx.AsyncClient*)."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout, headers=_DEFAULT_HEADERS)

        self.history: List[Message] = []
        self.conversation_id: str | None = None
        self.server_state: ServerState | None = None

        self._streaming_response: Optional[httpx.Response] = None

    def new_conversation(self) -> None:
        """Reset local state – start fresh conversation."""
        self.history.clear()
        self.conversation_id = None
        self.server_state = None

    async def ask(self, message: str, *, context: Dict[str, Any] | None = None) -> str:
        """Convenience wrapper around :py:meth:`send_message`.

        Collects the streaming response and returns the final assistant text.
        """
        parts: List[str] = []
        async for chunk in self.send_message(message, context=context):
            if chunk.type is ChatResponseType.TEXT:
                parts.append(chunk.content)
        return "".join(parts)

    async def send_message(
        self,
        message: str,
        *,
        context: Dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Asynchronous version of :py:meth:`RagbitsChatClient.send_message`."""

        user_msg = Message(role=MessageRole.USER, content=message)
        self.history.append(user_msg)
        assistant_reply = Message(role=MessageRole.ASSISTANT, content="")
        self.history.append(assistant_reply)
        assistant_index = len(self.history) - 1

        merged_context: Dict[str, Any] = {}
        if self.server_state is not None:
            merged_context.update(self.server_state.model_dump())
        if self.conversation_id is not None:
            merged_context["conversation_id"] = self.conversation_id
        if context:
            merged_context.update(context)

        payload: Dict[str, Any] = {
            "message": message,
            "history": [m.model_dump() for m in map_history_to_messages(self.history)],
            "context": merged_context,
        }

        url = build_api_url(self._base_url, "/api/chat")

        async with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            self._streaming_response = resp

            async for raw_line in resp.aiter_lines():
                if not raw_line:
                    continue
                parsed = parse_sse_line(raw_line)
                if parsed is None:
                    continue
                await self._process_incoming(parsed, assistant_index)
                yield parsed

        self._streaming_response = None

    async def stop(self) -> None:
        """Abort currently running stream (if any)."""
        if self._streaming_response is not None and not self._streaming_response.is_closed:
            await self._streaming_response.aclose()
            self._streaming_response = None

    async def aclose(self) -> None:
        """Close the underlying *httpx.AsyncClient* session."""
        await self._client.aclose()

    async def _process_incoming(self, resp: ChatResponse, assistant_index: int) -> None:
        """Update local client-side state based on *resp*."""

        if resp.type is ChatResponseType.STATE_UPDATE:
            self.server_state = resp.content  # type: ignore[assignment]
        elif resp.type is ChatResponseType.CONVERSATION_ID:
            self.conversation_id = resp.content  # type: ignore[assignment]
        elif resp.type is ChatResponseType.MESSAGE_ID:
            pass
        elif resp.type is ChatResponseType.TEXT:
            assistant_msg = self.history[assistant_index]
            if isinstance(resp.content, str):
                assistant_msg.content += resp.content
        elif resp.type is ChatResponseType.REFERENCE:
            pass
