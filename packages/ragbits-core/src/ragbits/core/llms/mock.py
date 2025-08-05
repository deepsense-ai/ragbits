from collections.abc import AsyncGenerator, Iterable

from ragbits.core.llms.base import LLM, LLMOptions, ToolChoice
from ragbits.core.prompt import ChatFormat
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.types import NOT_GIVEN, NotGiven


class MockLLMOptions(LLMOptions):
    """
    Options for the MockLLM class.
    """

    response: str | NotGiven = NOT_GIVEN
    response_stream: list[str] | NotGiven = NOT_GIVEN
    tool_calls: list[dict] | NotGiven = NOT_GIVEN
    reasoning: str | NotGiven = NOT_GIVEN
    reasoning_stream: list[str] | NotGiven = NOT_GIVEN


class MockLLM(LLM[MockLLMOptions]):
    """
    Class for mocking interactions with LLMs - useful for testing.
    """

    options_cls = MockLLMOptions

    def __init__(
        self,
        model_name: str = "mock",
        default_options: MockLLMOptions | None = None,
        *,
        price_per_prompt_token: float = 0.0,
        price_per_completion_token: float = 0.0,
    ) -> None:
        """
        Constructs a new MockLLM instance.

        Args:
            model_name: Name of the model to be used.
            default_options: Default options to be used.
            price_per_prompt_token: The price per prompt token.
            price_per_completion_token: The price per completion token.
        """
        super().__init__(model_name, default_options=default_options)
        self.calls: list[ChatFormat] = []
        self.tool_choice: ToolChoice | None = None
        self._price_per_prompt_token = price_per_prompt_token
        self._price_per_completion_token = price_per_completion_token

    def get_model_id(self) -> str:
        """
        Returns the model id.
        """
        return "mock:" + self.model_name

    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Returns the estimated cost of the LLM call.
        """
        return self._price_per_prompt_token * prompt_tokens + self._price_per_completion_token * completion_tokens

    async def _call(  # noqa: PLR6301
        self,
        prompt: Iterable[BasePrompt],
        options: MockLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Mocks the call to the LLM, using the response from the options if provided.
        """
        prompt = list(prompt)
        self.calls.extend([p.chat for p in prompt])
        self.tool_choice = tool_choice
        response = "mocked response" if isinstance(options.response, NotGiven) else options.response
        reasoning = None if isinstance(options.reasoning, NotGiven) else options.reasoning
        tool_calls = (
            None
            if isinstance(options.tool_calls, NotGiven)
            or any(message["role"] == "tool" for p in prompt for message in p.chat)
            else options.tool_calls
        )
        return [
            {
                "response": response,
                "reasoning": reasoning,
                "tool_calls": tool_calls,
                "is_mocked": True,
                "throughput": 1 / len(prompt),
                "usage": {
                    "prompt_tokens": 10 * (i + 1),
                    "completion_tokens": 20 * (i + 1),
                    "total_tokens": 30 * (i + 1),
                },
            }
            for i in range(len(prompt))
        ]

    async def _call_streaming(  # noqa: PLR6301
        self,
        prompt: BasePrompt,
        options: MockLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Mocks the call to the LLM, using the response from the options if provided.
        """
        self.calls.append(prompt.chat)
        self.tool_choice = tool_choice

        async def generator() -> AsyncGenerator[dict, None]:
            if not isinstance(options.tool_calls, NotGiven) and not any(
                message["role"] == "tool" for message in prompt.chat
            ):
                yield {"tool_calls": options.tool_calls}
            elif not isinstance(options.response_stream, NotGiven):
                if not isinstance(options.reasoning_stream, NotGiven):
                    for reasoning in options.reasoning_stream:
                        yield {"response": reasoning, "reasoning": True}
                for response in options.response_stream:
                    yield {"response": response}
            elif not isinstance(options.response, NotGiven):
                if not isinstance(options.reasoning, NotGiven):
                    yield {"response": options.reasoning, "reasoning": True}
                yield {"response": options.response}

            else:
                yield {"response": "mocked response"}

            yield {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                }
            }

        return generator()
