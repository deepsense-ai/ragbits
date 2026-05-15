from ragbits.core.utils.chat_message_text import iter_text_segments_from_openai_message_content


def test_string_content() -> None:
    assert list(iter_text_segments_from_openai_message_content("hello")) == ["hello"]


def test_multimodal_text_parts() -> None:
    content = [
        {"type": "text", "text": "a"},
        {"type": "image_url", "image_url": {"url": "x"}},
        {"type": "text", "text": "b"},
    ]
    assert list(iter_text_segments_from_openai_message_content(content)) == ["a", "b"]


def test_none_content() -> None:
    assert list(iter_text_segments_from_openai_message_content(None)) == []
