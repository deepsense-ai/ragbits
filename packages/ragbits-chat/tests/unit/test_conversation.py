from collections.abc import AsyncGenerator, Generator
from types import TracebackType
from typing import Any, cast
from unittest.mock import patch

import httpx
import pytest

from ragbits.chat.client.conversation import RagbitsConversation, SyncRagbitsConversation
from ragbits.chat.client.exceptions import ChatClientResponseError
from ragbits.chat.interface.types import ChatResponseType, Message, MessageRole, StateUpdate


class _DummyStreamResponse:
    """Synchronous dummy response emulating the httpx streaming interface."""

    def __init__(self, lines: list[str], *, status_code: int = 200):
        self._lines = lines
        self.status_code = status_code
        self._closed = False

    def iter_lines(self) -> Generator[str, None, None]:
        yield from self._lines

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=httpx.Request("GET", "http://host"), response=httpx.Response(self.status_code)
            )

    def __enter__(self) -> "_DummyStreamResponse":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed


class _DummyAsyncStreamResponse:
    """Asynchronous dummy response emulating the httpx streaming interface."""

    def __init__(self, lines: list[str], *, status_code: int = 200):
        self._lines = lines
        self.status_code = status_code
        self._closed = False

    async def aiter_lines(self) -> AsyncGenerator[str, None]:
        for line in self._lines:
            yield line

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=httpx.Request("GET", "http://host"), response=httpx.Response(self.status_code)
            )

    async def __aenter__(self) -> "_DummyAsyncStreamResponse":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed


@pytest.fixture
def sse_lines() -> list[str]:
    """Representative SSE lines covering all supported ChatResponse types."""
    return [
        'data: {"type": "conversation_id", "content": "cid"}\n\n',
        'data: {"type": "state_update", "content": {"state": {"x": 1}, "signature": "sig"}}\n\n',
        'data: {"type": "message_id", "content": "mid"}\n\n',
        'data: {"type": "text", "content": "foo"}\n\n',
        'data: {"type": "reference", "content": {"title": "Doc", "content": "Body", "url": null}}\n\n',
        'data: {"type": "text", "content": " bar"}\n\n',
    ]


def test_send_message_yields_responses_sync(sse_lines: list[str]) -> None:
    """send_message must yield ChatResponse instances in order and update state."""
    http_client = httpx.Client()
    with patch.object(http_client, "stream", return_value=_DummyStreamResponse(sse_lines)):
        conv = SyncRagbitsConversation(base_url="http://host", http_client=http_client)
        responses = list(conv.run_streaming("hi"))
    assert [r.type for r in responses] == [
        ChatResponseType.CONVERSATION_ID,
        ChatResponseType.STATE_UPDATE,
        ChatResponseType.MESSAGE_ID,
        ChatResponseType.TEXT,
        ChatResponseType.REFERENCE,
        ChatResponseType.TEXT,
    ]
    assert conv.conversation_id == "cid"
    assert conv.conversation_state is not None
    assert conv.conversation_state.state == {"x": 1}
    assert "foo" in conv.history[-1].content
    assert "bar" in conv.history[-1].content
    assert "[REFERENCE]:" in conv.history[-1].content


def test_history_excludes_system_messages() -> None:
    """System messages must not be forwarded to the server in the payload."""
    sent_payload: dict[str, Any] = {}

    def _mock_stream(method: str, url: str, json: dict[str, Any]) -> _DummyStreamResponse:
        nonlocal sent_payload
        sent_payload = json
        return _DummyStreamResponse([])

    http_client = httpx.Client()
    conv = SyncRagbitsConversation(base_url="x", http_client=http_client)
    conv.history.append(Message(role=MessageRole.SYSTEM, content="sys"))
    with patch.object(http_client, "stream", side_effect=_mock_stream):
        list(conv.run_streaming("hello"))
    assert all(msg["role"] != MessageRole.SYSTEM.value for msg in sent_payload["history"])


def test_context_merging() -> None:
    """send_message must merge server_state, conversation_id and custom context."""
    captured: dict[str, Any] = {}

    def _mock_stream(method: str, url: str, json: dict[str, Any]) -> _DummyStreamResponse:
        nonlocal captured
        captured = json
        return _DummyStreamResponse([])

    http_client = httpx.Client()
    conv = SyncRagbitsConversation(base_url="x", http_client=http_client)
    conv.conversation_state = StateUpdate(state={"a": 1}, signature="sig")
    conv.conversation_id = "c1"
    with patch.object(http_client, "stream", side_effect=_mock_stream):
        list(conv.run_streaming("question", context={"b": 2}))

    assert captured["context"]["conversation_id"] == "c1"
    assert captured["context"]["state"]["a"] == 1
    assert captured["context"]["b"] == 2


def test_sync_send_message_raises_on_status_error(sse_lines: list[str]) -> None:
    """HTTP error codes should raise ChatClientResponseError."""
    http_client = httpx.Client()
    with patch.object(http_client, "stream", return_value=_DummyStreamResponse(sse_lines, status_code=502)):
        conv = SyncRagbitsConversation(base_url="u", http_client=http_client)
        with pytest.raises(ChatClientResponseError):
            list(conv.run_streaming("boom"))


@pytest.mark.asyncio
async def test_send_message_yields_responses_async(sse_lines: list[str]) -> None:
    """RagbitsConversation must behave equivalently to its synchronous counterpart."""
    http_client = httpx.AsyncClient()
    with patch.object(http_client, "stream", return_value=_DummyAsyncStreamResponse(sse_lines)):
        conv = RagbitsConversation(base_url="h", http_client=http_client)
        collected = []
        async for chunk in conv.run_streaming("q"):
            collected.append(chunk)
    assert collected[0].type is ChatResponseType.CONVERSATION_ID
    assert collected[-1].type is ChatResponseType.TEXT
    assert "foo" in conv.history[-1].content
    assert "bar" in conv.history[-1].content
    assert "[REFERENCE]:" in conv.history[-1].content


@pytest.mark.asyncio
async def test_async_stop_closes_stream(sse_lines: list[str]) -> None:
    """Stop must close an active stream in RagbitsConversation."""
    resp = _DummyAsyncStreamResponse(sse_lines)
    conv = RagbitsConversation(base_url="h", http_client=httpx.AsyncClient())
    conv._streaming_response = cast(httpx.Response, resp)
    await conv.stop()
    assert resp.is_closed is True
    assert conv._streaming_response is None


def test_sync_stop_closes_stream(sse_lines: list[str]) -> None:
    """Stop must close an active stream in SyncRagbitsConversation."""
    resp = _DummyStreamResponse(sse_lines)
    conv = SyncRagbitsConversation(base_url="h", http_client=httpx.Client())
    conv._streaming_response = cast(httpx.Response, resp)
    conv.stop()
    assert resp.is_closed is True
    assert conv._streaming_response is None
