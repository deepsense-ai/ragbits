import asyncio
from collections.abc import AsyncGenerator, Generator
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ragbits.chat.clients.client.async_client import AsyncRagbitsChatClient
from ragbits.chat.clients.client.sync_client import RagbitsChatClient
from ragbits.chat.clients.conversation.async_conversation import AsyncConversation
from ragbits.chat.clients.conversation.sync_conversation import Conversation
from ragbits.chat.clients.exceptions import ChatClientRequestError, ChatClientResponseError


class _DummyStreamResponse:
    """A minimal synchronous response object emulating *httpx* streaming behaviour."""

    def __init__(self, lines: list[str], *, status_code: int = 200) -> None:
        self._lines = lines
        self.status_code = status_code
        self._closed = False

    def iter_lines(self) -> Generator[str, None, None]:
        """Yield pre-defined *lines* one by one."""
        yield from self._lines

    def raise_for_status(self) -> None:
        """Mimic successful response ― unless status code indicates error."""
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=httpx.Response(self.status_code))

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
    """Asynchronous counterpart to :class:`_DummyStreamResponse`."""

    def __init__(self, lines: list[str], *, status_code: int = 200) -> None:
        self._lines = lines
        self.status_code = status_code
        self._closed = False

    async def aiter_lines(self) -> AsyncGenerator[str, None]:
        for line in self._lines:
            yield line

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=httpx.Response(self.status_code))

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
    """Return a list of valid SSE lines covering all relevant response types."""
    return [
        'data: {"type": "conversation_id", "content": "conv123"}\n\n',
        'data: {"type": "state_update", "content": {"state": {"foo": "bar"}, "signature": "sig"}}\n\n',
        'data: {"type": "text", "content": "Hello"}\n\n',
        'data: {"type": "text", "content": " world"}\n\n',
    ]


def test_sync_conversation_ask_and_state_update(sse_lines: list[str]) -> None:
    """Ensure :pyclass:`Conversation.ask` correctly aggregates text and updates state."""
    http_client = httpx.Client()

    def _mock_stream(method: str, url: str, json: dict[str, Any]) -> _DummyStreamResponse:
        return _DummyStreamResponse(sse_lines)

    with patch.object(http_client, "stream", side_effect=_mock_stream):
        conv = Conversation(base_url="http://testserver", http_client=http_client)
        result = conv.ask("Hello")

    assert result == "Hello world"
    assert len(conv.history) == 2
    assert conv.history[0].role.value == "user"
    assert conv.history[0].content == "Hello"
    assert conv.history[1].role.value == "assistant"
    assert conv.history[1].content == "Hello world"
    assert conv.conversation_id == "conv123"
    assert conv.server_state is not None
    assert conv.server_state.state == {"foo": "bar"}


def test_sync_conversation_error_handling_response_error(sse_lines: list[str]) -> None:
    """Verify that HTTP *4xx/5xx* responses are mapped to *ChatClientResponseError*."""
    failing_resp = _DummyStreamResponse(sse_lines, status_code=500)

    http_client = httpx.Client()

    def _mock_stream(method: str, url: str, json: dict[str, Any]) -> _DummyStreamResponse:
        return failing_resp

    with patch.object(http_client, "stream", side_effect=_mock_stream):
        conv = Conversation(base_url="http://testserver", http_client=http_client)
        with pytest.raises(ChatClientResponseError):
            conv.ask("Hello")


def test_sync_conversation_error_handling_request_error() -> None:
    """Verify transport-level errors bubble up as *ChatClientRequestError*."""
    http_client = httpx.Client()

    def _mock_stream(method: str, url: str, json: dict[str, Any]) -> _DummyStreamResponse:
        raise httpx.RequestError("boom", request=httpx.Request("POST", url))

    with patch.object(http_client, "stream", side_effect=_mock_stream):
        conv = Conversation(base_url="http://testserver", http_client=http_client)
        with pytest.raises(ChatClientRequestError):
            next(conv.send_message("Hello"))


def test_sync_chat_client_ask_proxy() -> None:
    """Ensure *RagbitsChatClient.ask* delegates to a fresh *Conversation*."""
    with patch("ragbits.chat.clients.conversation.sync_conversation.Conversation") as MockConv:
        mock_conv_instance = MockConv.return_value
        mock_conv_instance.ask.return_value = "answer"

        client = RagbitsChatClient(base_url="http://testserver")
        assert client.ask("question") == "answer"
        MockConv.assert_called_once_with(base_url="http://testserver", http_client=client._client)
        mock_conv_instance.ask.assert_called_once_with("question", context=None)


@pytest.mark.asyncio
async def test_async_conversation_ask_and_state_update(sse_lines: list[str]) -> None:
    """Same assertions as the sync variant but for *AsyncConversation*."""
    http_client = httpx.AsyncClient()

    def _mock_stream(method: str, url: str, json: dict[str, Any]) -> _DummyAsyncStreamResponse:
        return _DummyAsyncStreamResponse(sse_lines)

    with patch.object(http_client, "stream", side_effect=_mock_stream):
        conv = AsyncConversation(base_url="http://testserver", http_client=http_client)
        result = await conv.ask("Hello")

    assert result == "Hello world"
    assert len(conv.history) == 2
    assert conv.conversation_id == "conv123"
    assert conv.server_state is not None
    assert conv.server_state.state == {"foo": "bar"}


@pytest.mark.asyncio
async def test_async_chat_client_ask_proxy() -> None:
    """Ensure *AsyncRagbitsChatClient.ask* delegates to a fresh *AsyncConversation*."""
    with patch("ragbits.chat.clients.conversation.async_conversation.AsyncConversation") as MockConv:
        mock_conv_instance = MockConv.return_value
        mock_conv_instance.ask = MagicMock(return_value=asyncio.Future())
        mock_conv_instance.ask.return_value.set_result("answer")

        client = AsyncRagbitsChatClient(base_url="http://testserver")
        result = await client.ask("question")
        assert result == "answer"
        MockConv.assert_called_once_with(base_url="http://testserver", http_client=client._client)
        mock_conv_instance.ask.assert_called_once_with("question", context=None)


def test_conversation_stop_closes_stream(sse_lines: list[str]) -> None:
    """Calling *stop* must close the active streaming response and reset state."""
    response = _DummyStreamResponse(sse_lines)
    conv = Conversation(base_url="http://testserver", http_client=httpx.Client())
    conv._streaming_response = response

    conv.stop()

    assert response.is_closed is True
    assert conv._streaming_response is None
