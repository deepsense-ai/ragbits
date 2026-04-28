"""Helpers for manipulating agent conversation history (ChatFormat)."""

import json
from typing import Any

from ragbits.core.prompt.base import ChatFormat


def inject_tool_call(
    history: ChatFormat,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,  # noqa: ANN401
) -> ChatFormat:
    """
    Append a synthetic (tool_use, tool_result) pair to a conversation history.

    Used by the chat layer when it has executed a tool on the user's behalf
    (e.g., after a confirmation was approved) and needs the LLM to see the
    outcome without re-deciding the call itself.

    The returned list is a shallow copy with two messages appended in OpenAI's
    tool-use format — an ``assistant`` turn carrying the ``tool_calls`` block
    and a ``tool`` turn carrying the result keyed by ``tool_call_id``.

    Args:
        history: Current conversation history. Not mutated.
        tool_call_id: Identifier to thread the tool_use and tool messages.
        tool_name: Name of the tool that was invoked.
        arguments: Arguments the tool was invoked with.
        result: Tool output. Coerced to ``str``.

    Returns:
        A new ChatFormat with the two messages appended.
    """
    return [
        *history,
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(arguments)},
                }
            ],
        },
        {"role": "tool", "tool_call_id": tool_call_id, "content": str(result)},
    ]
