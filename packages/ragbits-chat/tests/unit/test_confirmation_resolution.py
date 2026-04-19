"""Tests for ChatInterface confirmation-resolution helpers."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest

from ragbits.agents._main import ToolCallResult
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponseUnion, TextContent, TextResponse


class _Dummy(ChatInterface):
    async def chat(  # type: ignore[override]
        self, message: str, history: Any, context: ChatContext
    ) -> AsyncGenerator[ChatResponseUnion, None]:
        yield TextResponse(content=TextContent(text="ok"))


def test_create_pending_confirmation_state_shape():
    """Helper returns a state dict keyed by confirmation_id with tool_call_id, name, args."""
    request = ConfirmationRequest(
        confirmation_id="conf_1",
        tool_call_id="call_1",
        tool_name="send_slack",
        tool_description="Send a slack message",
        arguments={"channel": "#general", "text": "hi"},
    )

    state = ChatInterface.create_pending_confirmation_state(request)

    assert state == {
        "pending_confirmations": {
            "conf_1": {
                "tool_call_id": "call_1",
                "tool_name": "send_slack",
                "arguments": {"channel": "#general", "text": "hi"},
            }
        }
    }


async def test_resolve_pending_confirmations_confirmed_executes_and_appends_history():
    """A confirmed pending causes execute_tool_directly to run and history to grow."""
    iface = _Dummy()

    agent = AsyncMock()
    agent.execute_tool_directly.return_value = ToolCallResult(
        id="call_1", name="send_slack", arguments={"channel": "#general", "text": "hi"}, result="sent"
    )

    context = ChatContext(
        state={
            "pending_confirmations": {
                "conf_1": {
                    "tool_call_id": "call_1",
                    "tool_name": "send_slack",
                    "arguments": {"channel": "#general", "text": "hi"},
                }
            }
        },
        tool_confirmations=[{"confirmation_id": "conf_1", "confirmed": True}],
    )
    history = [{"role": "user", "content": "send hi to #general"}]

    new_history, responses = await iface.resolve_pending_confirmations(agent, context, history)

    agent.execute_tool_directly.assert_awaited_once()
    call_kwargs = agent.execute_tool_directly.call_args.kwargs
    assert call_kwargs["tool_call_id"] == "call_1"
    assert call_kwargs["tool_name"] == "send_slack"
    assert call_kwargs["arguments"] == {"channel": "#general", "text": "hi"}

    assert len(new_history) == 3
    assert new_history[1]["role"] == "assistant"
    assert new_history[1]["tool_calls"][0]["id"] == "call_1"
    assert new_history[2] == {"role": "tool", "tool_call_id": "call_1", "content": "sent"}
    assert responses  # at least one UI response emitted


async def test_resolve_pending_confirmations_declined_skips_execution():
    """A declined pending injects a decline result; no tool execution happens."""
    iface = _Dummy()

    agent = AsyncMock()

    context = ChatContext(
        state={
            "pending_confirmations": {
                "conf_1": {
                    "tool_call_id": "call_1",
                    "tool_name": "delete_file",
                    "arguments": {"path": "x"},
                }
            }
        },
        tool_confirmations=[{"confirmation_id": "conf_1", "confirmed": False}],
    )

    new_history, _ = await iface.resolve_pending_confirmations(agent, context, [])

    agent.execute_tool_directly.assert_not_called()
    assert new_history[-1]["role"] == "tool"
    assert "declined" in new_history[-1]["content"].lower()


async def test_resolve_pending_confirmations_no_pending_returns_input_unchanged():
    """No pending_confirmations in state → history untouched, no responses, no execution."""
    iface = _Dummy()

    agent = AsyncMock()

    context = ChatContext(state={}, tool_confirmations=[])
    history = [{"role": "user", "content": "hi"}]

    new_history, responses = await iface.resolve_pending_confirmations(agent, context, history)

    agent.execute_tool_directly.assert_not_called()
    assert new_history == history
    assert responses == []


async def test_resolve_pending_confirmations_unknown_confirmation_id_is_ignored():
    """A tool_confirmations entry with no matching pending entry is a no-op (legacy flow still works)."""
    iface = _Dummy()

    agent = AsyncMock()

    context = ChatContext(
        state={"pending_confirmations": {}},
        tool_confirmations=[{"confirmation_id": "unknown", "confirmed": True}],
    )

    new_history, responses = await iface.resolve_pending_confirmations(agent, context, [])

    agent.execute_tool_directly.assert_not_called()
    assert new_history == []
    assert responses == []


@pytest.fixture(autouse=True)
def _secret_key(monkeypatch):
    monkeypatch.setenv("RAGBITS_SECRET_KEY", "test-secret")
