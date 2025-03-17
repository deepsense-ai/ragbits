from collections.abc import AsyncGenerator

from pydantic import BaseModel

from ragbits.core.llms.base import LLM
from ragbits.core.options import Options
from ragbits.core.prompt import ChatFormat
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.types import NOT_GIVEN, NotGiven


class MockLLMOptions(Options):
    """
    Options for the MockLLM class.
    """

    response: str | NotGiven = NOT_GIVEN
    response_stream: list[str] | NotGiven = NOT_GIVEN


class MockLLM(LLM[MockLLMOptions]):
    """
    Class for mocking interactions with LLMs - useful for testing.
    """

    options_cls = MockLLMOptions

    def __init__(self, model_name: str = "mock", default_options: MockLLMOptions | None = None) -> None:
        """
        Constructs a new MockLLM instance.

        Args:
            model_name: Name of the model to be used.
            default_options: Default options to be used.
        """
        super().__init__(model_name, default_options=default_options)
        self.calls: list[ChatFormat] = []

    async def _call(  # noqa: PLR6301
        self,
        prompt: BasePrompt,
        options: MockLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict:
        """
        Mocks the call to the LLM, using the response from the options if provided.
        """
        self.calls.append(prompt.chat)
        if not isinstance(options.response, NotGiven):
            return {"response": options.response, "is_mocked": True}
        return {"response": "mocked response", "is_mocked": True}

    async def _call_streaming(  # noqa: PLR6301
        self,
        prompt: BasePrompt,
        options: MockLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Mocks the call to the LLM, using the response from the options if provided.
        """
        self.calls.append(prompt.chat)

        async def generator() -> AsyncGenerator[str, None]:
            if not isinstance(options.response_stream, NotGiven):
                for response in options.response_stream:
                    yield response
            elif not isinstance(options.response, NotGiven):
                yield options.response
            else:
                yield "mocked response"

        return generator()
