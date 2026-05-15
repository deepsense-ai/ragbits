"""Extract plain text from OpenAI-format chat message content fields."""

from __future__ import annotations

from collections.abc import Iterator


def iter_text_segments_from_openai_message_content(content: object) -> Iterator[str]:
    """
    Yields user-visible text segments from a single message ``content`` field.

    Handles string content and multimodal ``list`` parts (``type: "text"`` only).
    """
    if isinstance(content, str):
        yield content
        return
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                yield str(part.get("text") or "")
        return
    if content is None:
        return
    yield str(content)
