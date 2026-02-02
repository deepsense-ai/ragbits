"""Shared fixtures for agent unit tests."""

import pytest

from ragbits.agents.hooks.types import (
    PostToolHookCallback,
    PostToolInput,
    PostToolOutput,
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
