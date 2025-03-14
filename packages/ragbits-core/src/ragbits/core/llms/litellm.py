from collections.abc import AsyncGenerator

import litellm
from litellm.utils import CustomStreamWrapper, ModelResponse
from pydantic import BaseModel

from ragbits.core.audit import trace
from ragbits.core.llms.base import LLM
from ragbits.core.llms.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMNotSupportingImagesError,
    LLMResponseError,
    LLMStatusError,
)
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePrompt, ChatFormat
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
    logprobs: bool | None | NotGiven = NOT_GIVEN
    top_logprobs: int | None | NotGiven = NOT_GIVEN
    logit_bias: dict | None | NotGiven = NOT_GIVEN
    mock_response: str | None | NotGiven = NOT_GIVEN


class LiteLLM(LLM[LiteLLMOptions]):
    """
    Class for interaction with any LLM supported by LiteLLM API.
    """

    options_cls = LiteLLMOptions

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        default_options: LiteLLMOptions | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        use_structured_output: bool = False,
        router: litellm.Router | None = None,
    ) -> None:
        """
        Constructs a new LiteLLM instance.

        Args:
            model_name: Name of the [LiteLLM supported model](https://docs.litellm.ai/docs/providers) to be used.\
                Default is "gpt-3.5-turbo".
            default_options: Default options to be used.
            base_url: Base URL of the LLM API.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/providers).
            api_version: API version to be used. If not specified, the default version will be used.
            use_structured_output: Whether to request a
                [structured output](https://docs.litellm.ai/docs/completion/json_mode#pass-in-json_schema)
                from the model. Default is False. Can only be combined with models that support structured output.
            router: Router to be used to [route requests](https://docs.litellm.ai/docs/routing) to different models.
        """
        super().__init__(model_name, default_options)
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version
        self.use_structured_output = use_structured_output
        self.router = router

    def count_tokens(self, prompt: BasePrompt) -> int:
        """
        Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(litellm.token_counter(model=self.model_name, text=message["content"]) for message in prompt.chat)

    async def _call(
        self,
        prompt: BasePrompt,
        options: LiteLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            prompt: BasePrompt object containing the conversation
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
            LLMNotSupportingImagesError: If the model does not support images.
        """
        if prompt.list_images() and not litellm.supports_vision(self.model_name):
            raise LLMNotSupportingImagesError()

        response_format = self._get_response_format(output_schema=output_schema, json_mode=json_mode)

        response = await self._get_litellm_response(
            conversation=prompt.chat,
            options=options,
            response_format=response_format,
        )
        if not response.choices:  # type: ignore
            raise LLMEmptyResponseError()
        results = {}
        results["response"] = response.choices[0].message.content  # type: ignore

        if response.usage:  # type: ignore
            results["completion_tokens"] = response.usage.completion_tokens  # type: ignore
            results["prompt_tokens"] = response.usage.prompt_tokens  # type: ignore
            results["total_tokens"] = response.usage.total_tokens  # type: ignore

        if options.logprobs:
            results["logprobs"] = response.choices[0].logprobs["content"]  # type: ignore

        return results  # type: ignore

    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: LiteLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            prompt: BasePrompt object containing the conversation
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
            LLMNotSupportingImagesError: If the model does not support images.
        """
        if prompt.list_images() and not litellm.supports_vision(self.model_name):
            raise LLMNotSupportingImagesError()

        response_format = self._get_response_format(output_schema=output_schema, json_mode=json_mode)

        with trace(
            messages=prompt.chat,
            model=self.model_name,
            base_url=self.base_url,
            api_version=self.api_version,
            response_format=response_format,
            options=options.dict(),
        ) as outputs:
            response = await self._get_litellm_response(
                conversation=prompt.chat,
                options=options,
                response_format=response_format,
                stream=True,
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
