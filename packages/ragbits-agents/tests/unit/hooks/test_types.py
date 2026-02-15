"""Tests for hook type definitions."""

# ruff: noqa: PLR6301

import pytest

from ragbits.core.llms.base import ToolCall


class TestToolCallDecisionFields:
    def test_pass_decision_defaults(self):
        tc = ToolCall(id="1", type="function", name="test", arguments='{"a": 1}')  # type: ignore[arg-type]

        assert tc.decision == "pass"
        assert tc.reason is None

    def test_deny_decision(self):
        tc = ToolCall(id="1", type="function", name="test", arguments='{"a": 1}')  # type: ignore[arg-type]
        denied = tc.model_copy(update={"decision": "deny", "reason": "Not allowed"})

        assert denied.decision == "deny"
        assert denied.reason == "Not allowed"

    def test_ask_decision(self):
        tc = ToolCall(id="1", type="function", name="test", arguments='{"a": 1}')  # type: ignore[arg-type]
        ask = tc.model_copy(update={"decision": "ask", "reason": "Confirm?"})

        assert ask.decision == "ask"
        assert ask.reason == "Confirm?"

    def test_model_copy_preserves_existing_fields(self):
        tc = ToolCall(id="1", type="function", name="test", arguments='{"a": 1}')  # type: ignore[arg-type]
        modified = tc.model_copy(update={"decision": "deny", "reason": "blocked"})

        assert modified.id == "1"
        assert modified.name == "test"
        assert modified.arguments == {"a": 1}

    def test_decision_reason_validation_in_manager(self):
        """Decision/reason validation is now done by the HookManager, not the type itself."""
        # ToolCall allows any combination — manager enforces the constraint
        tc = ToolCall(id="1", type="function", name="test", arguments='{"a": 1}')  # type: ignore[arg-type]
        denied_no_reason = tc.model_copy(update={"decision": "deny"})
        assert denied_no_reason.decision == "deny"
        assert denied_no_reason.reason is None
