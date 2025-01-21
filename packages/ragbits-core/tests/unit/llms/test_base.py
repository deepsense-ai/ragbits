from collections.abc import AsyncGenerator

import pytest
from pydantic import BaseModel

from ragbits.core.llms.base import LLM
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePromptWithParser, ChatFormat, SimplePrompt


class DummyOptions(Options):
    pass


class DummyLLM(LLM[DummyOptions]):
    options_cls = DummyOptions

    @staticmethod
    async def _call(
        conversation: ChatFormat,
        options: DummyOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict:
        return {"response": "test response"}

    @staticmethod
    async def _call_streaming(
        conversation: ChatFormat,
        options: DummyOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        async def generate() -> AsyncGenerator[str, None]:
            yield "test response"

        return generate()


class CustomOutputType(BaseModel):
    message: str


class CustomPrompt(BasePromptWithParser[CustomOutputType]):
    def __init__(self, content: str) -> None:
        self._content = content

    @property
    def chat(self) -> ChatFormat:
        return [{"role": "user", "content": self._content}]

    @staticmethod
    def parse_response(response: str) -> CustomOutputType:
        return CustomOutputType(message=response)


@pytest.mark.asyncio
async def test_generate_with_str():
    llm = DummyLLM("test-model")
    response = await llm.generate("Hello")
    assert response == "test response"


@pytest.mark.asyncio
async def test_generate_with_chat_format():
    llm = DummyLLM("test-model")
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    response = await llm.generate(chat)
    assert response == "test response"


@pytest.mark.asyncio
async def test_generate_with_base_prompt():
    llm = DummyLLM("test-model")
    prompt = SimplePrompt("Hello")
    response = await llm.generate(prompt)
    assert response == "test response"


@pytest.mark.asyncio
async def test_generate_with_parser_prompt():
    llm = DummyLLM("test-model")
    prompt = CustomPrompt("Hello")
    response = await llm.generate(prompt)
    assert isinstance(response, CustomOutputType)
    assert response.message == "test response"


def test_init_with_str():
    prompt = SimplePrompt("Hello")
    assert prompt.chat == [{"role": "user", "content": "Hello"}]


def test_init_with_chat_format():
    chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
    prompt = SimplePrompt(chat)
    assert prompt.chat == chat


def test_json_mode():
    prompt = SimplePrompt("Hello")
    assert prompt.json_mode is False


def test_output_schema():
    prompt = SimplePrompt("Hello")
    assert prompt.output_schema() is None


def test_list_images():
    prompt = SimplePrompt("Hello")
    assert prompt.list_images() == []
