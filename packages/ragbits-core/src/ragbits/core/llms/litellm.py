import time
from collections.abc import AsyncGenerator, Callable
from typing import Any

import litellm
import tiktoken
from litellm.utils import CustomStreamWrapper, ModelResponse
from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.audit.metrics import HistogramMetric, record
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
        api_base: str | None = None,
        base_url: str | None = None,  # Alias for api_base
        api_key: str | None = None,
        api_version: str | None = None,
        use_structured_output: bool = False,
        router: litellm.Router | None = None,
        custom_model_cost_config: dict | None = None,
    ) -> None:
        """
        Constructs a new LiteLLM instance.

        Args:
            model_name: Name of the [LiteLLM supported model](https://docs.litellm.ai/docs/providers) to be used.\
                Default is "gpt-3.5-turbo".
            default_options: Default options to be used.
            api_base: Base URL of the LLM API.
            base_url: Alias for api_base. If both are provided, api_base takes precedence.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/providers).
            api_version: API version to be used. If not specified, the default version will be used.
            use_structured_output: Whether to request a
                [structured output](https://docs.litellm.ai/docs/completion/json_mode#pass-in-json_schema)
                from the model. Default is False. Can only be combined with models that support structured output.
            router: Router to be used to [route requests](https://docs.litellm.ai/docs/routing) to different models.
            custom_model_cost_config: Custom cost and capabilities configuration for the model.
                Necessary for custom model cost and capabilities tracking in LiteLLM.
                See the [LiteLLM documentation](https://docs.litellm.ai/docs/completion/token_usage#9-register_model)
                for more information.
        """
        super().__init__(model_name, default_options)
        self.api_base = api_base or base_url
        self.api_key = api_key
        self.api_version = api_version
        self.use_structured_output = use_structured_output
        self.router = router
        self.custom_model_cost_config = custom_model_cost_config
        if custom_model_cost_config:
            litellm.register_model(custom_model_cost_config)

    def count_tokens(self, prompt: BasePrompt) -> int:
        """
        Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(litellm.token_counter(model=self.model_name, text=message["content"]) for message in prompt.chat)

    def get_token_id(self, token: str) -> int:
        """
        Gets token id.

        Args:
            token: The token to encode.

        Returns:
            The id for the given token.
        """
        try:
            tokenizer = tiktoken.encoding_for_model(self.model_name)
            return tokenizer.encode_single_token(token)
        except KeyError:
            return litellm.encode(model=self.model_name, text=token)[0]

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

        start_time = time.perf_counter()
        response = await self._get_litellm_response(
            conversation=prompt.chat,
            options=options,
            response_format=response_format,
        )
        prompt_throughput = time.perf_counter() - start_time

        if not response.choices:  # type: ignore
            raise LLMEmptyResponseError()

        results = {}
        results["response"] = response.choices[0].message.content  # type: ignore

        if options.logprobs:
            results["logprobs"] = response.choices[0].logprobs["content"]  # type: ignore

        if response.usage:  # type: ignore
            results["completion_tokens"] = response.usage.completion_tokens  # type: ignore
            results["prompt_tokens"] = response.usage.prompt_tokens  # type: ignore
            results["total_tokens"] = response.usage.total_tokens  # type: ignore

            record(
                metric=HistogramMetric.INPUT_TOKENS,
                value=response.usage.prompt_tokens,  # type: ignore
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )
            record(
                metric=HistogramMetric.TOKEN_THROUGHPUT,
                value=response.usage.total_tokens / prompt_throughput,  # type: ignore
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )

        record(
            metric=HistogramMetric.PROMPT_THROUGHPUT,
            value=prompt_throughput,
            model=self.model_name,
            prompt=prompt.__class__.__name__,
        )

        return results

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
        input_tokens = self.count_tokens(prompt)
        start_time = time.perf_counter()

        response = await self._get_litellm_response(
            conversation=prompt.chat,
            options=options,
            response_format=response_format,
            stream=True,
        )
        if not response.completion_stream:  # type: ignore
            raise LLMEmptyResponseError()

        async def response_to_async_generator(response: CustomStreamWrapper) -> AsyncGenerator[str, None]:
            output_tokens = 0
            async for item in response:
                if content := item.choices[0].delta.content:
                    output_tokens += 1
                    if output_tokens == 1:
                        record(
                            metric=HistogramMetric.TIME_TO_FIRST_TOKEN,
                            value=time.perf_counter() - start_time,
                            model=self.model_name,
                            prompt=prompt.__class__.__name__,
                        )
                    yield content

            total_time = time.perf_counter() - start_time

            record(
                metric=HistogramMetric.INPUT_TOKENS,
                value=input_tokens,
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )
            record(
                metric=HistogramMetric.TOKEN_THROUGHPUT,
                value=output_tokens / total_time,
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )
            record(
                metric=HistogramMetric.PROMPT_THROUGHPUT,
                value=total_time,
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )

        return response_to_async_generator(response)  # type: ignore

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
                base_url=self.api_base,
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

    @property
    def base_url(self) -> str | None:
        """
        Returns the base URL of the LLM API. Alias for `api_base`.
        """
        return self.api_base

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Self:
        """
        Creates and returns a LiteLLM instance.

        Args:
            config: A configuration object containing the configuration for initializing the LiteLLM instance.

        Returns:
            LiteLLM: An initialized LiteLLM instance.
        """
        if "router" in config:
            router = litellm.router.Router(model_list=config["router"])
            config["router"] = router

        # Map base_url to api_base if present
        if "base_url" in config and "api_base" not in config:
            config["api_base"] = config.pop("base_url")

        return super().from_config(config)

    def __reduce__(self) -> tuple[Callable, tuple]:
        config = {
            "model_name": self.model_name,
            "default_options": self.default_options.dict(),
            "api_base": self.api_base,
            "api_key": self.api_key,
            "api_version": self.api_version,
            "use_structured_output": self.use_structured_output,
            "custom_model_cost_config": self.custom_model_cost_config,
        }
        if self.router:
            config["router"] = self.router.model_list
        return self.from_config, (config,)
