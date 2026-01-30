"""Tests for the HookManager class."""

# ruff: noqa: PLR6301

import hashlib
import json
from collections.abc import Callable

import pytest

from ragbits.agents._main import AgentRunContext
from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.manager import CONFIRMATION_ID_LENGTH, HookManager
from ragbits.agents.hooks.types import (
    EventType,
    PostToolHookCallback,
    PreToolHookCallback,
    PreToolInput,
    PreToolOutput,
)
from ragbits.core.llms.base import ToolCall


@pytest.fixture
def context() -> AgentRunContext:
    return AgentRunContext()


def make_confirmation_id(hook_name: str, tool_name: str, arguments: dict) -> str:
    """Generate a confirmation ID matching the manager's logic."""
    confirmation_str = f"{hook_name}:{tool_name}:{json.dumps(arguments, sort_keys=True)}"
    return hashlib.sha256(confirmation_str.encode()).hexdigest()[:CONFIRMATION_ID_LENGTH]


class TestHookRegistration:
    def test_register_and_retrieve_hooks(self, pass_hook: PreToolHookCallback):
        manager = HookManager()
        hook = Hook(event_type=EventType.PRE_TOOL, callback=pass_hook)
        manager.register(hook)

        hooks = manager.get_hooks(EventType.PRE_TOOL, tool_name=None)
        assert len(hooks) == 1
        assert hooks[0] == hook

    def test_hooks_sorted_by_priority(self, pass_hook: PreToolHookCallback):
        manager = HookManager(
            hooks=[
                Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, priority=100),
                Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, priority=10),
                Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, priority=50),
            ]
        )

        hooks = manager.get_hooks(EventType.PRE_TOOL, tool_name=None)
        assert [h.priority for h in hooks] == [10, 50, 100]


class TestHookRetrieval:
    def test_filters_by_tool_name(self, pass_hook: PreToolHookCallback):
        manager = HookManager(
            hooks=[
                Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, tool_names=["tool1"]),
                Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, tool_names=["tool2"]),
                Hook(event_type=EventType.PRE_TOOL, callback=pass_hook, tool_names=None),  # universal
            ]
        )

        assert len(manager.get_hooks(EventType.PRE_TOOL, "tool1")) == 2  # tool1 + universal
        assert len(manager.get_hooks(EventType.PRE_TOOL, tool_name=None)) == 3
        assert len(manager.get_hooks(EventType.POST_TOOL, tool_name=None)) == 0


class TestPreToolExecution:
    @pytest.mark.asyncio
    async def test_no_hooks_returns_pass(self, tool_call: ToolCall, context: AgentRunContext):
        result = await HookManager().execute_pre_tool(tool_call, context)

        assert result.decision == "pass"
        assert result.arguments == tool_call.arguments

    @pytest.mark.asyncio
    async def test_deny_stops_execution(self, tool_call: ToolCall, context: AgentRunContext):
        execution_order: list[str] = []

        async def tracking_deny_hook(input_data: PreToolInput) -> PreToolOutput:
            execution_order.append("deny")
            return PreToolOutput(arguments=input_data.tool_call.arguments, decision="deny", reason="Denied")

        async def tracking_pass_hook(input_data: PreToolInput) -> PreToolOutput:
            execution_order.append("pass")
            return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

        manager = HookManager(
            hooks=[
                Hook(event_type=EventType.PRE_TOOL, callback=tracking_deny_hook, priority=1),
                Hook(event_type=EventType.PRE_TOOL, callback=tracking_pass_hook, priority=2),
            ]
        )
        result = await manager.execute_pre_tool(tool_call, context)

        assert result.decision == "deny"
        assert execution_order == ["deny"]

    @pytest.mark.asyncio
    async def test_ask_creates_confirmation_request(
        self, tool_call: ToolCall, context: AgentRunContext, ask_hook: PreToolHookCallback
    ):
        manager = HookManager(hooks=[Hook(event_type=EventType.PRE_TOOL, callback=ask_hook)])
        result = await manager.execute_pre_tool(tool_call, context)

        assert result.decision == "ask"
        assert result.confirmation_request is not None
        assert result.confirmation_request.tool_name == tool_call.name
        assert len(result.confirmation_request.confirmation_id) == CONFIRMATION_ID_LENGTH

    @pytest.mark.asyncio
    async def test_ask_with_prior_confirmation(self, tool_call: ToolCall, ask_hook: PreToolHookCallback):
        manager = HookManager(hooks=[Hook(event_type=EventType.PRE_TOOL, callback=ask_hook)])
        confirmation_id = make_confirmation_id("ask_hook", "test_tool", {"arg1": "value1"})

        # Approved
        ctx_approved: AgentRunContext = AgentRunContext(
            tool_confirmations=[{"confirmation_id": confirmation_id, "confirmed": True}]
        )
        assert (await manager.execute_pre_tool(tool_call, ctx_approved)).decision == "pass"

        # Declined
        ctx_declined: AgentRunContext = AgentRunContext(
            tool_confirmations=[{"confirmation_id": confirmation_id, "confirmed": False}]
        )
        assert (await manager.execute_pre_tool(tool_call, ctx_declined)).decision == "deny"

    @pytest.mark.asyncio
    async def test_argument_chaining(
        self, tool_call: ToolCall, context: AgentRunContext, add_field: Callable[..., PreToolHookCallback]
    ):
        manager = HookManager(
            hooks=[
                Hook(event_type=EventType.PRE_TOOL, callback=add_field("hook1"), priority=1),
                Hook(event_type=EventType.PRE_TOOL, callback=add_field("hook2"), priority=2),
            ]
        )
        result = await manager.execute_pre_tool(tool_call, context)

        assert result.arguments == {"arg1": "value1", "hook1": "added", "hook2": "added"}


class TestPostToolExecution:
    @pytest.mark.asyncio
    async def test_output_chaining(self, tool_call: ToolCall, append_output: Callable[..., PostToolHookCallback]):
        manager = HookManager(
            hooks=[
                Hook(event_type=EventType.POST_TOOL, callback=append_output(" + h1"), priority=1),
                Hook(event_type=EventType.POST_TOOL, callback=append_output(" + h2"), priority=2),
            ]
        )
        result = await manager.execute_post_tool(tool_call, output="Original", error=None)

        assert result.output == "Original + h1 + h2"


class TestConfirmationIdGeneration:
    def test_deterministic_and_unique(self):
        # Same inputs = same ID
        assert make_confirmation_id("hook", "tool", {"a": 1}) == make_confirmation_id("hook", "tool", {"a": 1})

        # Different inputs = different IDs
        ids = [
            make_confirmation_id("hook1", "tool", {"a": 1}),
            make_confirmation_id("hook2", "tool", {"a": 1}),
            make_confirmation_id("hook", "tool1", {"a": 1}),
            make_confirmation_id("hook", "tool", {"a": 2}),
        ]
        assert len(set(ids)) == 4  # all unique

    def test_argument_order_independent(self):
        id1 = make_confirmation_id("hook", "tool", {"a": 1, "b": 2})
        id2 = make_confirmation_id("hook", "tool", {"b": 2, "a": 1})
        assert id1 == id2

    def test_correct_length(self):
        assert len(make_confirmation_id("hook", "tool", {})) == CONFIRMATION_ID_LENGTH
