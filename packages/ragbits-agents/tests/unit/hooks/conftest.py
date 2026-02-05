"""Fixtures specific to hooks tests."""

import pytest

from ragbits.core.llms.base import ToolCall


@pytest.fixture
def tool_call() -> ToolCall:
    return ToolCall(id="test-id", name="test_tool", arguments='{"arg1": "value1"}', type="function")  # type: ignore[arg-type]
