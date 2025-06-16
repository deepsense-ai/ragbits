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
    tool_calls: list[dict] | NotGiven = NOT_GIVEN


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
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Mocks the call to the LLM, using the response from the options if provided.
        """
        self.calls.append(prompt.chat)
        response = "mocked response" if isinstance(options.response, NotGiven) else options.response

        tool_calls = (
            None
            if isinstance(options.tool_calls, NotGiven) or any(message["role"] == "tool" for message in prompt.chat)
            else options.tool_calls
        )
        return {"response": response, "tool_calls": tool_calls, "is_mocked": True}

    async def _call_streaming(  # noqa: PLR6301
        self,
        prompt: BasePrompt,
        options: MockLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Mocks the call to the LLM, using the response from the options if provided.
        """
        self.calls.append(prompt.chat)

        async def generator() -> AsyncGenerator[dict, None]:
            if not isinstance(options.tool_calls, NotGiven) and not any(
                message["role"] == "tool" for message in prompt.chat
            ):
                yield {"tool_calls": options.tool_calls}
            elif not isinstance(options.response_stream, NotGiven):
                for response in options.response_stream:
                    yield {"response": response}
            elif not isinstance(options.response, NotGiven):
                yield {"response": options.response}
            else:
                yield {"response": "mocked response"}

        return generator()
