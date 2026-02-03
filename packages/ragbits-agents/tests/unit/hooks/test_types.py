"""Tests for hook type definitions."""

# ruff: noqa: PLR6301

import pytest

from ragbits.agents.confirmation import ConfirmationRequest
from ragbits.agents.hooks.types import (
    EventType,
    PostRunInput,
    PostRunOutput,
    PostToolInput,
    PostToolOutput,
    PreRunInput,
    PreRunOutput,
    PreToolInput,
    PreToolOutput,
)
from ragbits.agents.tool import ToolReturn
from ragbits.core.llms.base import ToolCall


class TestPreToolInput:
    def test_creation(self, tool_call: ToolCall):
        input_data = PreToolInput(tool_call=tool_call)

        assert input_data.event_type == EventType.PRE_TOOL
        assert input_data.tool_call.name == "test_tool"


class TestPreToolOutput:
    def test_pass_decision_defaults(self):
        output = PreToolOutput(arguments={"arg1": "value1"})

        assert output.decision == "pass"
        assert output.reason is None
        assert output.confirmation_request is None

    def test_deny_decision_requires_reason(self):
        with pytest.raises(ValueError, match="reason is required"):
            PreToolOutput(arguments={}, decision="deny")

        output = PreToolOutput(arguments={}, decision="deny", reason="Not allowed")
        assert output.decision == "deny"
        assert output.reason == "Not allowed"

    def test_ask_decision_requires_reason(self):
        with pytest.raises(ValueError, match="reason is required"):
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
    def test_creation_with_output(self, tool_call: ToolCall):
        input_data = PostToolInput(tool_call=tool_call, tool_return=ToolReturn(value="result"))
        assert input_data.event_type == EventType.POST_TOOL
        assert input_data.tool_return.value == "result"


class TestPostToolOutput:
    def test_creation_with_various_outputs(self):
        string_output = PostToolOutput(tool_return=ToolReturn("string"))
        assert string_output.tool_return.value == "string"

        dict_output = PostToolOutput(tool_return=ToolReturn({"key": "value"}))
        assert dict_output.tool_return.value == {"key": "value"}


class TestPreRunInput:
    def test_creation(self):
        input_data = PreRunInput(input="test query", options=None, context=None)

        assert input_data.event_type == EventType.PRE_RUN
        assert input_data.input == "test query"


class TestPreRunOutput:
    def test_creation(self):
        output = PreRunOutput(output="modified query")

        assert output.event_type == EventType.PRE_RUN
        assert output.output == "modified query"


class TestPostRunInput:
    def test_creation(self):
        mock_result = type("AgentResult", (), {"content": "response"})()
        input_data = PostRunInput(result=mock_result, options=None, context=None)

        assert input_data.event_type == EventType.POST_RUN
        assert input_data.result.content == "response"


class TestPostRunOutput:
    def test_creation(self):
        mock_result = type("AgentResult", (), {"content": "response"})()
        output = PostRunOutput(result=mock_result)

        assert output.event_type == EventType.POST_RUN
        assert output.rerun is False
        assert output.correction_prompt is None

    def test_with_rerun_and_correction(self):
        mock_result = type("AgentResult", (), {"content": "response"})()
        output = PostRunOutput(result=mock_result, rerun=True, correction_prompt="Please fix this")

        assert output.rerun is True
        assert output.correction_prompt == "Please fix this"
