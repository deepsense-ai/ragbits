"""Shared fixtures for agent unit tests."""

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

# Reusable hook callbacks as fixtures


@pytest.fixture
def pass_hook() -> PreToolHookCallback:
    async def pass_hook(input_data: PreToolInput) -> PreToolOutput:
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="pass")

    return pass_hook


@pytest.fixture
def deny_hook() -> PreToolHookCallback:
    async def deny_hook(input_data: PreToolInput) -> PreToolOutput:
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="deny", reason="Blocked by hook")

    return deny_hook


@pytest.fixture
def ask_hook() -> PreToolHookCallback:
    async def ask_hook(input_data: PreToolInput) -> PreToolOutput:
        return PreToolOutput(arguments=input_data.tool_call.arguments, decision="ask", reason="Needs confirmation")

    return ask_hook


# Hook factories for creating parameterized hooks


@pytest.fixture
def add_field():
    """Factory to create pre-tool hooks that add a field to arguments."""

    def factory(field: str, value: str = "added") -> PreToolHookCallback:
        async def hook(input_data: PreToolInput) -> PreToolOutput:
            args = dict(input_data.tool_call.arguments)
            args[field] = value
            return PreToolOutput(arguments=args, decision="pass")

        return hook

    return factory


@pytest.fixture
def append_output():
    """Factory to create post-tool hooks that append/prepend to output."""

    def factory(text: str, prepend: bool = False) -> PostToolHookCallback:
        async def hook(input_data: PostToolInput) -> PostToolOutput:
            tool_return_value = input_data.tool_return.value if input_data.tool_return is not None else None
            if prepend:
                return PostToolOutput(tool_return=ToolReturn(f"{text}{tool_return_value}"))
            return PostToolOutput(tool_return=ToolReturn(f"{tool_return_value}{text}"))

        return hook

    return factory


# Run hooks fixtures


@pytest.fixture
def modify_input():
    """Factory to create pre-run hooks that modify input."""

    def factory(prefix: str) -> PreRunHookCallback:
        async def hook(input_data: PreRunInput) -> PreRunOutput:
            modified = f"{prefix}: {input_data.input}" if input_data.input else prefix
            return PreRunOutput(output=modified)

        return hook

    return factory


@pytest.fixture
def post_run_pass() -> PostRunHookCallback:
    """Post-run hook that passes through the result."""

    async def hook(input_data: PostRunInput) -> PostRunOutput:
        return PostRunOutput(result=input_data.result)

    return hook
