"""Tests for hook type definitions."""

# ruff: noqa: PLR6301

import pytest
from pydantic import ValidationError

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.hooks.types import (
    EventType,
    PostToolInput,
    PostToolOutput,
    PreToolInput,
    PreToolOutput,
)
from ragbits.core.llms.base import ToolCall


class TestPreToolInput:
    def test_creation_with_frozen_event_type(self, tool_call: ToolCall):
        input_data = PreToolInput(tool_call=tool_call)

        assert input_data.event_type == EventType.PRE_TOOL
        assert input_data.tool_call.name == "test_tool"

        with pytest.raises(ValidationError):
            input_data.event_type = EventType.POST_TOOL  # type: ignore[assignment]


class TestPreToolOutput:
    def test_pass_decision_defaults(self):
        output = PreToolOutput(arguments={"arg1": "value1"})

        assert output.decision == "pass"
        assert output.reason is None
        assert output.confirmation_request is None

    def test_deny_decision_requires_reason(self):
        with pytest.raises(ValidationError, match="reason is required"):
            PreToolOutput(arguments={}, decision="deny")

        output = PreToolOutput(arguments={}, decision="deny", reason="Not allowed")
        assert output.decision == "deny"
        assert output.reason == "Not allowed"

    def test_ask_decision_requires_reason(self):
        with pytest.raises(ValidationError, match="reason is required"):
            PreToolOutput(arguments={}, decision="ask")

        output = PreToolOutput(arguments={}, decision="ask", reason="Confirm?")
        assert output.decision == "ask"

    def test_with_confirmation_request(self):
        confirmation = ConfirmationRequest(
            confirmation_id="abc123",
            tool_name="dangerous_tool",
            tool_description="A dangerous tool",
            arguments={"target": "something"},
        )
        output = PreToolOutput(
            arguments={},
            decision="ask",
            reason="Confirm",
            confirmation_request=confirmation,
        )

        assert output.confirmation_request is not None
        assert output.confirmation_request.confirmation_id == "abc123"
        assert output.confirmation_request.tool_name == "dangerous_tool"


class TestPostToolInput:
    def test_creation_with_output_and_error(self, tool_call: ToolCall):
        input_data = PostToolInput(tool_call=tool_call, output="result")
        assert input_data.event_type == EventType.POST_TOOL
        assert input_data.output == "result"
        assert input_data.error is None

        error = ValueError("failed")
        input_with_error = PostToolInput(tool_call=tool_call, output=None, error=error)
        assert input_with_error.error == error


class TestPostToolOutput:
    def test_creation_with_various_outputs(self):
        assert PostToolOutput(output="string").output == "string"
        assert PostToolOutput(output={"key": "value"}).output == {"key": "value"}
        assert PostToolOutput(output=None).output is None
