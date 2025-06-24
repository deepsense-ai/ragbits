from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import httpx

from ..._utils import build_api_url, parse_sse_line
from ...interface.types import (
    ChatResponse,
    ChatResponseType,
    Message,
    MessageRole,
    StateUpdate,
)
from ..base import AsyncConversationBase
from ..exceptions import ChatClientRequestError, ChatClientResponseError

__all__ = ["AsyncConversation"]


class AsyncConversation(AsyncConversationBase):
    """Represents a single **asynchronous** chat conversation."""

    def __init__(self, *, base_url: str, http_client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = http_client

        self.history: list[Message] = []
        self.conversation_id: str | None = None
        self.server_state: StateUpdate | None = None
        self._streaming_response: httpx.Response | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ask(self, message: str, *, context: dict[str, Any] | None = None) -> str:  # noqa: D401
        """Send *message* and return the final assistant reply."""
        parts: list[str] = []
        async for chunk in self.send_message(message, context=context):
            if chunk.type is ChatResponseType.TEXT:
                parts.append(str(chunk.content))
        return "".join(parts)

    async def send_message(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Asynchronous version of :py:meth:`Conversation.send_message`."""
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
            "history": [m.model_dump() for m in self.history if m.role is not MessageRole.SYSTEM],
            "context": merged_context,
        }

        url = build_api_url(self._base_url, "/api/chat")

        try:
            async with self._client.stream("POST", url, json=payload) as resp:
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ChatClientResponseError(
                        f"Unexpected response from {url}: {exc.response.status_code}"
                    ) from exc

                self._streaming_response = resp

                async for raw_line in resp.aiter_lines():
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

    async def stop(self) -> None:
        """Abort currently running stream (if any)."""
        if self._streaming_response is not None and not self._streaming_response.is_closed:
            await self._streaming_response.aclose()
            self._streaming_response = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_incoming(self, resp: ChatResponse, assistant_index: int) -> None:
        if resp.type is ChatResponseType.STATE_UPDATE and isinstance(resp.content, StateUpdate):
            self.server_state = resp.content
        elif resp.type is ChatResponseType.CONVERSATION_ID and isinstance(resp.content, str):
            self.conversation_id = resp.content
        elif resp.type is ChatResponseType.MESSAGE_ID:
            pass
        elif resp.type is ChatResponseType.TEXT:
            assistant_msg = self.history[assistant_index]
            if isinstance(resp.content, str):
                assistant_msg.content += resp.content
        elif resp.type is ChatResponseType.REFERENCE:
            pass
