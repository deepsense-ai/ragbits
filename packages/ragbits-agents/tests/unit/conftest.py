"""Shared fixtures for agent unit tests."""

from collections.abc import Callable

import pytest

from ragbits.agents.hooks.types import (
    PostRunHookCallback,
    PostRunInput,
    PostRunOutput,
    PostToolHookCallback,
    PostToolInput,
    PostToolOutput,
    PreRunHookCallback,
    PreRunInput,
    PreRunOutput,
    PreToolHookCallback,
    PreToolInput,
    PreToolOutput,
)
from ragbits.agents.tool import ToolReturn


@pytest.fixture
def pass_hook() -> PreToolHookCallback:
    """Pre-tool hook that allows execution to proceed."""

    async def pass_hook(input_data: PreToolInput) -> PreToolOutput:
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    return pass_hook


@pytest.fixture
def deny_hook() -> PreToolHookCallback:
    """Pre-tool hook that blocks execution."""

    async def deny_hook(input_data: PreToolInput) -> PreToolOutput:
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="deny", reason="Blocked by hook")

    return deny_hook


@pytest.fixture
def ask_hook() -> PreToolHookCallback:
    """Pre-tool hook that requests user confirmation."""

    async def ask_hook(input_data: PreToolInput) -> PreToolOutput:
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="ask", reason="Needs confirmation")

    return ask_hook


@pytest.fixture
def pre_tool_add_field() -> Callable[..., PreToolHookCallback]:
    """Factory to create pre-tool hooks that add a field to arguments."""

    def factory(field: str, value: str = "added") -> PreToolHookCallback:
        async def add_field_hook(input_data: PreToolInput) -> PreToolOutput:
            args = dict(input_data.tool_call.arguments)
            args[field] = value
            return PreToolOutput(arguments=args, decision="pass")

        return add_field_hook

    return factory


@pytest.fixture
def post_tool_append() -> Callable[..., PostToolHookCallback]:
    """Factory to create post-tool hooks that append/prepend to output."""

    def factory(text: str, prepend: bool = False) -> PostToolHookCallback:
        async def append_output_hook(input_data: PostToolInput) -> PostToolOutput:
            tool_return_value = input_data.tool_return.value if input_data.tool_return is not None else None
            if prepend:
                return PostToolOutput(tool_return=ToolReturn(f"{text}{tool_return_value}"))
            return PostToolOutput(tool_return=ToolReturn(f"{tool_return_value}{text}"))

        return append_output_hook

    return factory


@pytest.fixture
def pre_run_modify() -> Callable[..., PreRunHookCallback]:
    """Factory to create pre-run hooks that modify input with a prefix."""

    def factory(prefix: str) -> PreRunHookCallback:
        async def modify_input_hook(input_data: PreRunInput) -> PreRunOutput:
            modified = f"{prefix}: {input_data.input}" if input_data.input else prefix
            return PreRunOutput(output=modified)

        return modify_input_hook

    return factory


@pytest.fixture
def post_run_modify() -> Callable[..., PostRunHookCallback]:
    """Factory to create post-run hooks that modify the result content."""

    def factory(prefix: str) -> PostRunHookCallback:
        async def modify_result_hook(input_data: PostRunInput) -> PostRunOutput:
            modified = type("AgentResult", (), {"content": f"{prefix}: {input_data.result.content}"})()
            return PostRunOutput(result=modified)

        return modify_result_hook

    return factory
