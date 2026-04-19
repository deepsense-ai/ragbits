"""Tests for history manipulation helpers."""

import json

from ragbits.agents.history import inject_tool_call


def test_inject_tool_call_appends_assistant_and_tool_messages():
    """Injection produces an assistant tool_use message followed by a tool result message."""
    history = [{"role": "user", "content": "delete foo.txt"}]

    result = inject_tool_call(
        history,
        tool_call_id="call_42",
        tool_name="delete_file",
        arguments={"path": "foo.txt"},
        result="Deleted foo.txt",
    )

    assert len(result) == 3
    assert result[0] == {"role": "user", "content": "delete foo.txt"}

    assistant_msg = result[1]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] is None
    assert assistant_msg["tool_calls"] == [
        {
            "id": "call_42",
            "type": "function",
            "function": {"name": "delete_file", "arguments": json.dumps({"path": "foo.txt"})},
        }
    ]

    tool_msg = result[2]
    assert tool_msg == {"role": "tool", "tool_call_id": "call_42", "content": "Deleted foo.txt"}


def test_inject_tool_call_does_not_mutate_input():
    """Helper returns a new list; caller's history is untouched."""
    history = [{"role": "user", "content": "hi"}]

    inject_tool_call(
        history, tool_call_id="c", tool_name="t", arguments={}, result="ok"
    )

    assert history == [{"role": "user", "content": "hi"}]


def test_inject_tool_call_stringifies_non_string_result():
    """Non-string results are coerced to str (matching add_tool_use_message)."""
    result = inject_tool_call(
        [], tool_call_id="c", tool_name="t", arguments={}, result={"key": "value"}
    )

    assert result[1]["content"] == str({"key": "value"})
