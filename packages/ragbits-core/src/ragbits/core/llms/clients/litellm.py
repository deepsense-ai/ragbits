from collections.abc import AsyncGenerator

import litellm
from litellm.utils import CustomStreamWrapper, ModelResponse
from pydantic import BaseModel

from ragbits.core.audit import trace
from ragbits.core.llms.clients.base import LLMClient
from ragbits.core.llms.clients.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMResponseError,
    LLMStatusError,
)
from ragbits.core.options import Options
from ragbits.core.prompt import ChatFormat
from ragbits.core.types import NOT_GIVEN, NotGiven


class LiteLLMOptions(Options):
    """
    Dataclass that represents all available LLM call options for the LiteLLM client.
    Each of them is described in the [LiteLLM documentation](https://docs.litellm.ai/docs/completion/input).
    """

    frequency_penalty: float | None | NotGiven = NOT_GIVEN
    max_tokens: int | None | NotGiven = NOT_GIVEN
    n: int | None | NotGiven = NOT_GIVEN
    presence_penalty: float | None | NotGiven = NOT_GIVEN
    seed: int | None | NotGiven = NOT_GIVEN
    stop: str | list[str] | None | NotGiven = NOT_GIVEN
    temperature: float | None | NotGiven = NOT_GIVEN
    top_p: float | None | NotGiven = NOT_GIVEN
    mock_response: str | None | NotGiven = NOT_GIVEN


class LiteLLMClient(LLMClient[LiteLLMOptions]):
    """
    Client for the LiteLLM that supports calls to 100+ LLMs APIs, including OpenAI, Anthropic, VertexAI,
    Hugging Face and others.
    """

    _options_cls = LiteLLMOptions

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        use_structured_output: bool = False,
        router: litellm.Router | None = None,
    ) -> None:
        """
        Constructs a new LiteLLMClient instance.

        Args:
            model_name: Name of the model to use.
            base_url: Base URL of the LLM API.
            api_key: API key used to authenticate with the LLM API.
            api_version: API version of the LLM API.
            use_structured_output: Whether to request a structured output from the model. Default is False.
            router: Router to be used to route requests to different models.
        """
        super().__init__(model_name)
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version
        self.use_structured_output = use_structured_output
        self.router = router

    async def call(
        self,
        conversation: ChatFormat,
        options: LiteLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> str:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Output schema for requesting a specific response format.
            Only used if the client has been initialized with `use_structured_output=True`.

        Returns:
            Response string from LLM.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
        """
        response_format = self._get_response_format(output_schema=output_schema, json_mode=json_mode)

        with trace(
            messages=conversation,
            model=self.model_name,
            base_url=self.base_url,
            api_version=self.api_version,
            response_format=response_format,
            options=options.dict(),
        ) as outputs:
            response = await self._get_litellm_response(
                conversation=conversation, options=options, response_format=response_format
            )

            if not response.choices:  # type: ignore
                raise LLMEmptyResponseError()

            outputs.response = response.choices[0].message.content  # type: ignore
            if response.usage:  # type: ignore
                outputs.completion_tokens = response.usage.completion_tokens  # type: ignore
                outputs.prompt_tokens = response.usage.prompt_tokens  # type: ignore
                outputs.total_tokens = response.usage.total_tokens  # type: ignore

        return outputs.response  # type: ignore

    async def call_streaming(
        self,
        conversation: ChatFormat,
        options: LiteLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format.
            output_schema: Output schema for requesting a specific response format.
            Only used if the client has been initialized with `use_structured_output=True`.

        Returns:
            Response string from LLM.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
        """
        response_format = self._get_response_format(output_schema=output_schema, json_mode=json_mode)
        with trace(
            messages=conversation,
            model=self.model_name,
            base_url=self.base_url,
            api_version=self.api_version,
            response_format=response_format,
            options=options.dict(),
        ) as outputs:
            response = await self._get_litellm_response(
                conversation=conversation, options=options, response_format=response_format, stream=True
            )

            if not response.completion_stream:  # type: ignore
                raise LLMEmptyResponseError()

            async def response_to_async_generator(response: CustomStreamWrapper) -> AsyncGenerator[str, None]:
                async for item in response:
                    yield item.choices[0].delta.content or ""

            outputs.response = response_to_async_generator(response)  # type: ignore
        return outputs.response  # type: ignore

    async def _get_litellm_response(
        self,
        conversation: ChatFormat,
        options: LiteLLMOptions,
        response_format: type[BaseModel] | dict | None,
        stream: bool = False,
    ) -> ModelResponse | CustomStreamWrapper:
        entrypoint = self.router or litellm

        try:
            response = await entrypoint.acompletion(
                messages=conversation,
                model=self.model_name,
                base_url=self.base_url,
                api_key=self.api_key,
                api_version=self.api_version,
                response_format=response_format,
                stream=stream,
                **options.dict(),
            )
        except litellm.openai.APIConnectionError as exc:
            raise LLMConnectionError() from exc
        except litellm.openai.APIStatusError as exc:
            raise LLMStatusError(exc.message, exc.status_code) from exc
        except litellm.openai.APIResponseValidationError as exc:
            raise LLMResponseError() from exc
        return response

    def _get_response_format(
        self, output_schema: type[BaseModel] | dict | None, json_mode: bool
    ) -> type[BaseModel] | dict | None:
        supported_params = litellm.get_supported_openai_params(model=self.model_name)

        response_format = None
        if supported_params is not None and "response_format" in supported_params:
            if output_schema is not None and self.use_structured_output:
                response_format = output_schema
            elif json_mode:
                response_format = {"type": "json_object"}
        return response_format
