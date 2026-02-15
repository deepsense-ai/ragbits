"""Tests for the Hook base class."""

# ruff: noqa: PLR6301

import pytest

from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.types import EventType, PreToolCallback
from ragbits.core.llms.base import ToolCall


class TestHookToolMatching:
    def test_matches_tool_when_in_list(self, pass_hook: PreToolCallback):
        hook = Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, tool_names=["tool1", "tool2"])
        assert hook.matches_tool("tool1") is True
        assert hook.matches_tool("other") is False

    def test_matches_all_tools_when_tools_is_none(self, pass_hook: PreToolCallback):
        hook = Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, tool_names=None)
        assert hook.matches_tool("anything") is True


class TestHookExecution:
    @pytest.mark.asyncio
    async def test_execute_calls_callback(self, tool_call: ToolCall):
        async def modify_args(tool_call: ToolCall) -> ToolCall:
            args = dict(tool_call.arguments)
            args["added"] = True
            return tool_call.model_copy(update={"arguments": args})

        hook = Hook(event_type=EventType.PRE_TOOL, callback=modify_args)
        result = await hook.callback(tool_call)

        assert result.arguments["added"] is True
        assert result.decision == "pass"
