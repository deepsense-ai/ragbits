from __future__ import annotations

from collections.abc import Generator
from typing import Any

import httpx

from .._utils import build_api_url, parse_sse_line
from .base import SyncChatClientBase
from .exceptions import ChatClientRequestError, ChatClientResponseError
from .types import (
    ChatResponse,
    ChatResponseType,
    Message,
    MessageRole,
    ServerState,
    map_history_to_messages,
)

__all__ = ["RagbitsChatClient"]

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}


class RagbitsChatClient(SyncChatClientBase):
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
        """Reset local state – start a fresh conversation."""
        self.history.clear()
        self.conversation_id = None
        self.server_state = None

    def ask(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Send *message* and return the final assistant reply.

        Internally this collects the *text* chunks returned by
        :py:meth:`send_message` and concatenates them into a single string.
        """
        assistant_reply_parts: list[str] = []
        for chunk in self.send_message(message, context=context):
            if chunk.type is ChatResponseType.TEXT:
                assistant_reply_parts.append(str(chunk.content))
        return "".join(assistant_reply_parts)

    def send_message(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""
        user_msg = Message(role=MessageRole.USER, content=message)
        self.history.append(user_msg)

        assistant_reply = Message(role=MessageRole.ASSISTANT, content="")
        self.history.append(assistant_reply)
        assistant_index = len(self.history) - 1

        merged_context: dict[str, Any] = {}
        if self.server_state is not None:
            merged_context.update(self.server_state.model_dump())
        if self.conversation_id is not None:
            merged_context["conversation_id"] = self.conversation_id
        if context:
            merged_context.update(context)

        payload: dict[str, Any] = {
            "message": message,
            "history": [m.model_dump() for m in map_history_to_messages(self.history)],
            "context": merged_context,
        }

        url = build_api_url(self._base_url, "/api/chat")

        try:
            with self._client.stream("POST", url, json=payload) as resp:
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ChatClientResponseError(
                        f"Unexpected response from {url}: {exc.response.status_code}"
                    ) from exc

                self._streaming_response = resp

                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    parsed = parse_sse_line(raw_line)
                    if parsed is None:
                        continue

                    self._process_incoming(parsed, assistant_index)
                    yield parsed
        except httpx.RequestError as exc:
            raise ChatClientRequestError(f"Error communicating with {url}: {exc}") from exc
        finally:
            self._streaming_response = None

    def stop(self) -> None:
        """Abort currently running stream (if any)."""
        if self._streaming_response is not None and not self._streaming_response.is_closed:
            self._streaming_response.close()
            self._streaming_response = None

    def _process_incoming(self, resp: ChatResponse, assistant_index: int) -> None:
        """Update local client-side state based on *resp*."""
        if resp.type is ChatResponseType.STATE_UPDATE:
            self.server_state = resp.content
        elif resp.type is ChatResponseType.CONVERSATION_ID:
            self.conversation_id = resp.content
        elif resp.type is ChatResponseType.MESSAGE_ID:
            pass
        elif resp.type is ChatResponseType.TEXT:
            assistant_msg = self.history[assistant_index]
            if isinstance(resp.content, str):
                assistant_msg.content += resp.content
        elif resp.type is ChatResponseType.REFERENCE:
            pass
