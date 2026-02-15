"""Shared fixtures for agent unit tests."""

from collections.abc import Callable

import pytest

from ragbits.agents.hooks.types import (
    OnEventCallback,
    PostRunCallback,
    PostToolCallback,
    PreRunCallback,
    PreToolCallback,
)
from ragbits.agents.tool import ToolCallResult, ToolReturn
from ragbits.core.llms.base import ToolCall


@pytest.fixture
def pass_hook() -> PreToolCallback:
    """Pre-tool hook that allows execution to proceed."""

    async def pass_hook(tool_call: ToolCall) -> ToolCall:
        return tool_call

    return pass_hook


@pytest.fixture
def deny_hook() -> PreToolCallback:
    """Pre-tool hook that blocks execution."""

    async def deny_hook(tool_call: ToolCall) -> ToolCall:
        return tool_call.model_copy(update={"decision": "deny", "reason": "Blocked by hook"})

    return deny_hook


@pytest.fixture
def ask_hook() -> PreToolCallback:
    """Pre-tool hook that requests user confirmation."""

    async def ask_hook(tool_call: ToolCall) -> ToolCall:
        return tool_call.model_copy(update={"decision": "ask", "reason": "Needs confirmation"})

    return ask_hook


@pytest.fixture
def pre_tool_add_field() -> Callable[..., PreToolCallback]:
    """Factory to create pre-tool hooks that add a field to arguments."""

    def factory(field: str, value: str = "added") -> PreToolCallback:
        async def add_field_hook(tool_call: ToolCall) -> ToolCall:
            args = dict(tool_call.arguments)
            args[field] = value
            return tool_call.model_copy(update={"arguments": args})

        return add_field_hook

    return factory


@pytest.fixture
def post_tool_append() -> Callable[..., PostToolCallback]:
    """Factory to create post-tool hooks that append/prepend to output."""

    def factory(text: str, prepend: bool = False) -> PostToolCallback:
        async def append_output_hook(tool_call: ToolCall, tool_return: ToolReturn) -> ToolReturn:
            tool_return_value = tool_return.value if tool_return is not None else None
            if prepend:
                return ToolReturn(f"{text}{tool_return_value}")
            return ToolReturn(f"{tool_return_value}{text}")

        return append_output_hook

    return factory


@pytest.fixture
def pre_run_modify() -> Callable[..., PreRunCallback]:
    """Factory to create pre-run hooks that modify input with a prefix."""

    def factory(prefix: str) -> PreRunCallback:
        async def modify_input_hook(input: str | None, options: object, context: object) -> str | None:
            modified = f"{prefix}: {input}" if input else prefix
            return modified

        return modify_input_hook

    return factory


@pytest.fixture
def post_run_modify() -> Callable[..., PostRunCallback]:
    """Factory to create post-run hooks that modify the result content."""

    def factory(prefix: str) -> PostRunCallback:
        async def modify_result_hook(result: object, options: object, context: object) -> object:
            modified = type("AgentResult", (), {"content": f"{prefix}: {result.content}"})()
            return modified

        return modify_result_hook

    return factory


@pytest.fixture
def on_event_word_filter() -> Callable[..., OnEventCallback]:
    """Factory to create ON_EVENT callbacks that filter words from str chunks."""

    def factory(word: str, replacement: str = "***") -> OnEventCallback:
        async def word_filter_hook(
            event: str | ToolCall | ToolCallResult,
            accumulated_content: str,
        ) -> str | ToolCall | ToolCallResult | None:
            if isinstance(event, str):
                return event.replace(word, replacement)
            return event

        return word_filter_hook

    return factory


@pytest.fixture
def on_event_modify_chunk() -> Callable[..., OnEventCallback]:
    """Factory to create ON_EVENT callbacks that modify str chunks with a prefix."""

    def factory(prefix: str) -> OnEventCallback:
        async def modify_chunk_hook(
            event: str | ToolCall | ToolCallResult,
            accumulated_content: str,
        ) -> str | ToolCall | ToolCallResult | None:
            if isinstance(event, str):
                return f"{prefix}{event}"
            return event

        return modify_chunk_hook

    return factory
