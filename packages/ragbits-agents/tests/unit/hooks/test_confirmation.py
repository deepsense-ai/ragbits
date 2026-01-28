"""Tests for the confirmation hook helper."""

# ruff: noqa: PLR6301

import pytest

from ragbits.agents.hooks.confirmation import requires_confirmation_hook
from ragbits.agents.hooks.types import EventType, PreToolInput
from ragbits.core.llms.base import ToolCall


class TestRequiresConfirmationHook:
    def test_creates_hook_with_defaults(self):
        hook = requires_confirmation_hook()

        assert hook.event_type == EventType.PRE_TOOL
        assert hook.priority == 1
        assert hook.tools is None

    def test_creates_hook_with_custom_options(self):
        hook = requires_confirmation_hook(tools=["delete_file"], priority=50)

        assert hook.tools == ["delete_file"]
        assert hook.priority == 50

    @pytest.mark.asyncio
    async def test_hook_returns_ask_decision_with_reason(self, tool_call: ToolCall):
        hook = requires_confirmation_hook()
        result = await hook.execute(PreToolInput(tool_call=tool_call))

        assert result.decision == "ask"
        assert result.arguments == tool_call.arguments
        assert result.reason is not None
        assert tool_call.name in result.reason
