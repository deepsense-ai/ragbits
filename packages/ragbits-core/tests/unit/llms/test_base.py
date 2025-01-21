import pytest
from pydantic import BaseModel
from typing import AsyncGenerator

from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePrompt, BasePromptWithParser, ChatFormat, SimplePrompt


class DummyOptions(Options):
    pass


class DummyLLM(LLM[DummyOptions]):
    options_cls = DummyOptions

    async def _call(
        self,
        conversation: ChatFormat,
        options: DummyOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict:
        return {"response": "test response"}

    async def _call_streaming(
        self,
        conversation: ChatFormat,
        options: DummyOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        yield "test response"


class CustomOutputType(BaseModel):
    message: str


class CustomPrompt(BasePromptWithParser[CustomOutputType]):
    def __init__(self, content: str) -> None:
        self._content = content

    @property
    def chat(self) -> ChatFormat:
        return [{"role": "user", "content": self._content}]

    def parse_response(self, response: str) -> CustomOutputType:
        return CustomOutputType(message=response)


@pytest.mark.asyncio
class TestLLM:
    async def test_generate_with_str(self):
        llm = DummyLLM("test-model")
        response = await llm.generate("Hello")
        assert response == "test response"

    async def test_generate_with_chat_format(self):
        llm = DummyLLM("test-model")
        chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
        response = await llm.generate(chat)
        assert response == "test response"

    async def test_generate_with_base_prompt(self):
        llm = DummyLLM("test-model")
        prompt = SimplePrompt("Hello")
        response = await llm.generate(prompt)
        assert response == "test response"

    async def test_generate_with_parser_prompt(self):
        llm = DummyLLM("test-model")
        prompt = CustomPrompt("Hello")
        response = await llm.generate(prompt)
        assert isinstance(response, CustomOutputType)
        assert response.message == "test response"


class TestSimplePrompt:
    def test_init_with_str(self):
        prompt = SimplePrompt("Hello")
        assert prompt.chat == [{"role": "user", "content": "Hello"}]

    def test_init_with_chat_format(self):
        chat = [{"role": "system", "content": "You are a helpful assistant"}, {"role": "user", "content": "Hello"}]
        prompt = SimplePrompt(chat)
        assert prompt.chat == chat

    def test_json_mode(self):
        prompt = SimplePrompt("Hello")
        assert prompt.json_mode is False

    def test_output_schema(self):
        prompt = SimplePrompt("Hello")
        assert prompt.output_schema() is None

    def test_list_images(self):
        prompt = SimplePrompt("Hello")
        assert prompt.list_images() == []
