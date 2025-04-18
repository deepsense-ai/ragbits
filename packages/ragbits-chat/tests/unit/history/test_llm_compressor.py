import pytest

from ragbits.chat.history.compressors.llm import LastMessageAndHistory, StandaloneMessageCompressor
from ragbits.core.llms.mock import MockLLM, MockLLMOptions
from ragbits.core.prompt import ChatFormat
from ragbits.core.prompt.prompt import Prompt


class MockPrompt(Prompt[LastMessageAndHistory, str]):
    user_prompt = "mock prompt"


async def test_messages_included():
    conversation: ChatFormat = [
        {"role": "user", "content": "foo1"},
        {"role": "assistant", "content": "foo2"},
        {"role": "user", "content": "foo3"},
    ]
    llm = MockLLM(default_options=MockLLMOptions(response="some answer"))
    compressor = StandaloneMessageCompressor(llm)
    answer = await compressor.compress(conversation)
    assert answer == "some answer"
    user_prompt = llm.calls[0][1]
    assert user_prompt["role"] == "user"
    content = user_prompt["content"]
    assert "foo1" in content
    assert "foo2" in content
    assert "foo3" in content


async def test_no_messages():
    conversation: ChatFormat = []
    compressor = StandaloneMessageCompressor(MockLLM())

    with pytest.raises(ValueError):
        await compressor.compress(conversation)


async def test_last_message_not_user():
    conversation: ChatFormat = [
        {"role": "assistant", "content": "foo2"},
    ]
    compressor = StandaloneMessageCompressor(MockLLM())

    with pytest.raises(ValueError):
        await compressor.compress(conversation)


async def test_history_len():
    conversation: ChatFormat = [
        {"role": "user", "content": "foo1"},
        {"role": "assistant", "content": "foo2"},
        {"role": "user", "content": "foo3"},
        {"role": "user", "content": "foo4"},
        {"role": "user", "content": "foo5"},
    ]
    llm = MockLLM()
    compressor = StandaloneMessageCompressor(llm, history_len=3)
    await compressor.compress(conversation)
    user_prompt = llm.calls[0][1]
    assert user_prompt["role"] == "user"
    content = user_prompt["content"]

    # The rephrased message should be included
    assert "foo5" in content

    # Three previous messages should be included
    assert "foo2" in content
    assert "foo3" in content
    assert "foo4" in content

    # Earlier messages should not be included
    assert "foo1" not in content


async def test_only_user_and_assistant_messages_in_history():
    conversation: ChatFormat = [
        {"role": "user", "content": "foo4"},
        {"role": "system", "content": "foo1"},
        {"role": "unknown", "content": "foo2"},
        {"role": "assistant", "content": "foo3"},
        {"role": "user", "content": "foo4"},
        {"role": "assistant", "content": "foo5"},
        {"role": "user", "content": "foo6"},
    ]
    llm = MockLLM()
    compressor = StandaloneMessageCompressor(llm, history_len=4)
    await compressor.compress(conversation)
    user_prompt = llm.calls[0][1]
    assert user_prompt["role"] == "user"
    content = user_prompt["content"]
    assert "foo4" in content
    assert "foo5" in content
    assert "foo6" in content
    assert "foo3" in content
    assert "foo1" not in content
    assert "foo2" not in content


async def test_changing_prompt():
    conversation: ChatFormat = [
        {"role": "user", "content": "foo1"},
        {"role": "assistant", "content": "foo2"},
        {"role": "user", "content": "foo3"},
    ]
    llm = MockLLM()
    compressor = StandaloneMessageCompressor(llm, prompt=MockPrompt)
    await compressor.compress(conversation)
    user_prompt = llm.calls[0][0]
    assert user_prompt["role"] == "user"
    assert user_prompt["content"] == "mock prompt"
