"""Tests for HookManager.execute_on_event()."""

from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any

import pytest

from ragbits.agents._main import DownstreamAgentResult
from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.hooks.base import Hook
from ragbits.agents.hooks.manager import HookManager
from ragbits.agents.hooks.types import EventType
from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms.base import ToolCall, Usage

_Event = str | ToolCall | ToolCallResult


async def _to_list(async_gen: AsyncGenerator[Any, None]) -> list[Any]:
    """Collect all items from an async generator."""
    items = []
    async for item in async_gen:
        items.append(item)
    return items


async def _async_gen(items: list[Any]) -> AsyncGenerator[Any, None]:
    """Create an async generator from a list of items."""
    for item in items:
        yield item


class TestNoHooks:
    @staticmethod
    @pytest.mark.asyncio
    async def test_str_events_pass_through() -> None:
        manager: HookManager[Any, Any, Any] = HookManager()
        events = ["Hello", " ", "World"]
        result = await _to_list(manager.execute_on_event(_async_gen(events)))
        assert result == ["Hello", " ", "World"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_mixed_events_pass_through() -> None:
        manager: HookManager[Any, Any, Any] = HookManager()
        tc = ToolCall(id="t1", name="test_tool", arguments='{"a": 1}', type="function")  # type: ignore[arg-type]
        tcr = ToolCallResult(id="t1", name="test_tool", arguments={"a": 1}, result="done")
        events = ["chunk", tc, tcr]
        result = await _to_list(manager.execute_on_event(_async_gen(events)))
        assert result == events


class TestStrChunkModification:
    @staticmethod
    @pytest.mark.asyncio
    async def test_hook_modifies_text_chunks() -> None:
        async def uppercase_hook(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, str):
                return event.upper()
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=uppercase_hook)]
        )
        events = ["hello", " world"]
        result = await _to_list(manager.execute_on_event(_async_gen(events)))
        assert result == ["HELLO", " WORLD"]


class TestStrChunkSuppression:
    @staticmethod
    @pytest.mark.asyncio
    async def test_hook_suppresses_chunk() -> None:
        async def suppress_empty(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, str) and event.strip() == "":
                return None
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=suppress_empty)]
        )
        events = ["hello", " ", "world"]
        result = await _to_list(manager.execute_on_event(_async_gen(events)))
        assert result == ["hello", "world"]


class TestAccumulatedContentTracking:
    @staticmethod
    @pytest.mark.asyncio
    async def test_accumulated_content_grows() -> None:
        seen_accumulated: list[str] = []

        async def tracking_hook(event: _Event, accumulated_content: str) -> _Event | None:
            seen_accumulated.append(accumulated_content)
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=tracking_hook)]
        )
        events = ["Hello", " ", "World"]
        await _to_list(manager.execute_on_event(_async_gen(events)))
        assert seen_accumulated == ["", "Hello", "Hello "]


class TestToolCallModification:
    @staticmethod
    @pytest.mark.asyncio
    async def test_hook_modifies_tool_call() -> None:
        async def add_arg_hook(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, ToolCall):
                args = dict(event.arguments)
                args["extra"] = "added"
                return event.model_copy(update={"arguments": args})
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=add_arg_hook)]
        )
        tc = ToolCall(id="t1", name="test_tool", arguments='{"a": 1}', type="function")  # type: ignore[arg-type]
        result = await _to_list(manager.execute_on_event(_async_gen([tc])))
        assert len(result) == 1
        assert result[0].arguments == {"a": 1, "extra": "added"}


class TestToolCallResultModification:
    @staticmethod
    @pytest.mark.asyncio
    async def test_hook_modifies_tool_call_result() -> None:
        async def modify_result_hook(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, ToolCallResult):
                return ToolCallResult(
                    id=event.id,
                    name=event.name,
                    arguments=event.arguments,
                    result=f"[MODIFIED] {event.result}",
                )
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=modify_result_hook)]
        )
        tcr = ToolCallResult(id="t1", name="test_tool", arguments={"a": 1}, result="original")
        result = await _to_list(manager.execute_on_event(_async_gen([tcr])))
        assert len(result) == 1
        assert result[0].result == "[MODIFIED] original"


class TestInfrastructureEventsPassThrough:
    @staticmethod
    @pytest.mark.asyncio
    async def test_usage_passes_through() -> None:
        called = False

        async def should_not_be_called(event: _Event, accumulated_content: str) -> _Event | None:
            nonlocal called
            called = True
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=should_not_be_called)]
        )
        usage = Usage()
        result = await _to_list(manager.execute_on_event(_async_gen([usage])))
        assert result == [usage]
        assert not called

    @staticmethod
    @pytest.mark.asyncio
    async def test_simple_namespace_passes_through() -> None:
        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=lambda e, a: e)]
        )
        ns = SimpleNamespace(result={"content": "test"})
        result = await _to_list(manager.execute_on_event(_async_gen([ns])))
        assert result == [ns]

    @staticmethod
    @pytest.mark.asyncio
    async def test_confirmation_request_passes_through() -> None:
        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=lambda e, a: e)]
        )
        cr = ConfirmationRequest(
            confirmation_id="abc123",
            tool_name="test_tool",
            tool_description="Test",
            arguments={},
        )
        result = await _to_list(manager.execute_on_event(_async_gen([cr])))
        assert result == [cr]

    @staticmethod
    @pytest.mark.asyncio
    async def test_downstream_agent_result_passes_through() -> None:
        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=lambda e, a: e)]
        )
        dar = DownstreamAgentResult(agent_id="agent1", item="chunk")
        result = await _to_list(manager.execute_on_event(_async_gen([dar])))
        assert result == [dar]


class TestHookChaining:
    @staticmethod
    @pytest.mark.asyncio
    async def test_multiple_hooks_chain_in_priority_order() -> None:
        async def add_prefix(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, str):
                return f"[A]{event}"
            return event

        async def add_suffix(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, str):
                return f"{event}[B]"
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[
                Hook(event_type=EventType.ON_EVENT, callback=add_prefix, priority=1),
                Hook(event_type=EventType.ON_EVENT, callback=add_suffix, priority=2),
            ]
        )
        result = await _to_list(manager.execute_on_event(_async_gen(["hello"])))
        assert result == ["[A]hello[B]"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_suppression_in_chain_stops_later_hooks() -> None:
        execution_order: list[str] = []

        async def suppress_hook(event: _Event, accumulated_content: str) -> None:
            execution_order.append("suppress")

        async def modify_hook(event: _Event, accumulated_content: str) -> _Event | None:
            execution_order.append("modify")
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[
                Hook(event_type=EventType.ON_EVENT, callback=suppress_hook, priority=1),
                Hook(event_type=EventType.ON_EVENT, callback=modify_hook, priority=2),
            ]
        )
        result = await _to_list(manager.execute_on_event(_async_gen(["hello"])))
        assert result == []
        assert execution_order == ["suppress"]


class TestToolNameFiltering:
    @staticmethod
    @pytest.mark.asyncio
    async def test_hook_with_tool_names_only_fires_for_matching() -> None:
        calls: list[ToolCall | ToolCallResult] = []

        async def tracking_hook(event: _Event, accumulated_content: str) -> _Event | None:
            calls.append(event)  # type: ignore[arg-type]
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[
                Hook(
                    event_type=EventType.ON_EVENT,
                    callback=tracking_hook,
                    tool_names=["target_tool"],
                )
            ]
        )
        tc_match = ToolCall(id="t1", name="target_tool", arguments="{}", type="function")  # type: ignore[arg-type]
        tc_no_match = ToolCall(id="t2", name="other_tool", arguments="{}", type="function")  # type: ignore[arg-type]
        str_chunk = "text"

        events = [str_chunk, tc_match, tc_no_match]
        result = await _to_list(manager.execute_on_event(_async_gen(events)))
        # All events pass through, but hook only called for matching tool
        assert result == events
        assert len(calls) == 1
        assert calls[0].name == "target_tool"

    @staticmethod
    @pytest.mark.asyncio
    async def test_tool_call_result_name_filtering() -> None:
        calls: list[ToolCall | ToolCallResult] = []

        async def tracking_hook(event: _Event, accumulated_content: str) -> _Event | None:
            calls.append(event)  # type: ignore[arg-type]
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[
                Hook(
                    event_type=EventType.ON_EVENT,
                    callback=tracking_hook,
                    tool_names=["target_tool"],
                )
            ]
        )
        tcr_match = ToolCallResult(id="t1", name="target_tool", arguments={}, result="ok")
        tcr_no_match = ToolCallResult(id="t2", name="other_tool", arguments={}, result="ok")

        result = await _to_list(manager.execute_on_event(_async_gen([tcr_match, tcr_no_match])))
        assert result == [tcr_match, tcr_no_match]
        assert len(calls) == 1
        assert calls[0].name == "target_tool"


class TestWordFilterUseCase:
    @staticmethod
    @pytest.mark.asyncio
    async def test_word_filter() -> None:
        async def filter_bad_words(event: _Event, accumulated_content: str) -> _Event | None:
            if isinstance(event, str):
                return event.replace("bad", "***")
            return event

        manager: HookManager[Any, Any, Any] = HookManager(
            hooks=[Hook(event_type=EventType.ON_EVENT, callback=filter_bad_words)]
        )
        events = ["This is ", "a bad ", "word"]
        result = await _to_list(manager.execute_on_event(_async_gen(events)))
        assert result == ["This is ", "a *** ", "word"]
