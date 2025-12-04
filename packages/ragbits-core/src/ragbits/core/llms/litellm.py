import asyncio
import time
from collections.abc import AsyncGenerator, Callable, Iterable
from typing import TYPE_CHECKING, Any, Literal

import tiktoken
from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.llms.base import LLM, LLMOptions, ToolChoice
from ragbits.core.llms.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMNotSupportingImagesError,
    LLMNotSupportingPdfsError,
    LLMNotSupportingReasoningEffortError,
    LLMNotSupportingToolUseError,
    LLMResponseError,
    LLMStatusError,
)
from ragbits.core.prompt.base import BasePrompt, ChatFormat
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.lazy_litellm import LazyLiteLLM

if TYPE_CHECKING:
    from litellm import CustomStreamWrapper, ModelResponse, Router


class LiteLLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the LiteLLM client.
    Each of them is described in the [LiteLLM documentation](https://docs.litellm.ai/docs/completion/input).
    Reasoning effort and thinking are described in [LiteLLM Reasoning documentation](https://docs.litellm.ai/docs/reasoning_content)
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
    tpm: int | None | NotGiven = NOT_GIVEN
    rpm: int | None | NotGiven = NOT_GIVEN
    reasoning_effort: Literal["low", "medium", "high"] | None | NotGiven = NOT_GIVEN
    thinking: dict | None | NotGiven = NOT_GIVEN


class LiteLLM(LLM[LiteLLMOptions], LazyLiteLLM):
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
        router: "Router | None" = None,
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
        self._cached_router: Router | None = None  # Cache for auto-created router
        if custom_model_cost_config:
            self._litellm.register_model(custom_model_cost_config)

    def get_model_id(self) -> str:
        """
        Returns the model id.
        """
        return "litellm:" + self.model_name

    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Returns the estimated cost of the LLM call.

        Args:
            prompt_tokens: The number of tokens in the prompt.
            completion_tokens: The number of tokens in the completion.

        Returns:
            The estimated cost of the LLM call.
        """
        response_cost = self._litellm.get_model_info(self.model_name)
        response_cost_input = prompt_tokens * response_cost["input_cost_per_token"]
        response_cost_output = completion_tokens * response_cost["output_cost_per_token"]
        return response_cost_input + response_cost_output

    def count_tokens(self, prompt: BasePrompt) -> int:
        """
        Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(
            self._litellm.token_counter(model=self.model_name, text=message.get("content") or "")
            for message in prompt.chat
        )

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
            return self._litellm.encode(model=self.model_name, text=token)[0]

    async def _call(
        self,
        prompt: Iterable[BasePrompt],
        options: LiteLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            prompt: Iterable of BasePrompt objects containing conversations
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools

        Returns:
            list of dictionaries with responses from the LLM and metadata.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
            LLMNotSupportingImagesError: If the model does not support images.
            LLMNotSupportingPdfsError: If the model does not support PDFs.
            LLMNotSupportingToolUseError: If the model does not support tool use.
        """
        if any(p.list_images() for p in prompt) and not self._litellm.supports_vision(self.model_name):
            raise LLMNotSupportingImagesError()

        if any(p.list_pdfs() for p in prompt) and not self._litellm.supports_pdf_input(self.model_name):
            raise LLMNotSupportingPdfsError()

        if tools and not self._litellm.supports_function_calling(self.model_name):
            raise LLMNotSupportingToolUseError()

        if options.reasoning_effort and not self._litellm.supports_reasoning(self.model_name):
            raise LLMNotSupportingReasoningEffortError(self.model_name)

        start_time = time.perf_counter()
        raw_responses = await asyncio.gather(
            *(
                self._get_litellm_response(
                    conversation=single_prompt.chat,
                    options=options,
                    response_format=self._get_response_format(
                        output_schema=single_prompt.output_schema(), json_mode=single_prompt.json_mode
                    ),
                    tools=tools,
                    tool_choice=tool_choice,
                )
                for single_prompt in prompt
            )
        )

        results: list[dict] = []
        throughput_batch = time.perf_counter() - start_time

        for response in raw_responses:
            if not response.choices:  # type: ignore
                raise LLMEmptyResponseError()

            result = {}
            result["response"] = response.choices[0].message.content  # type: ignore
            result["reasoning"] = getattr(response.choices[0].message, "reasoning_content", None)  # type: ignore
            result["throughput"] = throughput_batch / float(len(raw_responses))

            result["tool_calls"] = (
                [
                    {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                        "type": tool_call.type,
                        "id": tool_call.id,
                    }
                    for tool_call in tool_calls
                ]
                if tools and (tool_calls := response.choices[0].message.tool_calls)  # type: ignore
                else None
            )

            if options.logprobs:
                result["logprobs"] = response.choices[0].logprobs["content"]  # type: ignore

            if response.usage:  # type: ignore
                result["usage"] = {
                    "completion_tokens": response.usage.completion_tokens,  # type: ignore
                    "prompt_tokens": response.usage.prompt_tokens,  # type: ignore
                    "total_tokens": response.usage.total_tokens,  # type: ignore
                }

            results.append(result)

        return results

    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: LiteLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            prompt: BasePrompt object containing the conversation
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools

        Returns:
            Response string from LLM.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
            LLMNotSupportingImagesError: If the model does not support images.
            LLMNotSupportingPdfsError: If the model does not support PDFs.
            LLMNotSupportingToolUseError: If the model does not support tool use.
        """
        if prompt.list_images() and not self._litellm.supports_vision(self.model_name):
            raise LLMNotSupportingImagesError()

        if prompt.list_pdfs() and not self._litellm.supports_pdf_input(self.model_name):
            raise LLMNotSupportingPdfsError()

        if tools and not self._litellm.supports_function_calling(self.model_name):
            raise LLMNotSupportingToolUseError()

        if options.reasoning_effort and not self._litellm.supports_reasoning(self.model_name):
            raise LLMNotSupportingReasoningEffortError(self.model_name)

        response_format = self._get_response_format(output_schema=prompt.output_schema(), json_mode=prompt.json_mode)
        input_tokens = self.count_tokens(prompt)

        provider_calculated_usage = None

        start_time = time.perf_counter()
        response = await self._get_litellm_response(
            conversation=prompt.chat,
            options=options,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
            stream_options={"include_usage": True},
        )

        try:
            if (not response.completion_stream and not response.choices) and not response.reasoning:  # type: ignore
                raise LLMEmptyResponseError()
        except AttributeError:
            # some providers might not include some parameters (i.e. Gemini -> choices)
            pass

        async def response_to_async_generator(response: "CustomStreamWrapper") -> AsyncGenerator[dict, None]:
            nonlocal input_tokens, provider_calculated_usage
            output_tokens = 0
            tool_calls: list[dict] = []

            async for item in response:
                reasoning_content = getattr(item.choices[0].delta, "reasoning_content", None)
                if content := item.choices[0].delta.content or reasoning_content:
                    output_tokens += 1
                    if output_tokens == 1:
                        record_metric(
                            metric=LLMMetric.TIME_TO_FIRST_TOKEN,
                            value=time.perf_counter() - start_time,
                            metric_type=MetricType.HISTOGRAM,
                            model=self.model_name,
                            prompt=prompt.__class__.__name__,
                        )

                    yield {"response": content, "reasoning": bool(reasoning_content)}

                if tool_calls_delta := item.choices[0].delta.tool_calls:
                    for tool_call_chunk in tool_calls_delta:
                        while len(tool_calls) <= tool_call_chunk.index:
                            tool_calls.append({"id": "", "type": "", "name": "", "arguments": ""})

                        tool_calls[tool_call_chunk.index]["id"] += tool_call_chunk.id or ""
                        tool_calls[tool_call_chunk.index]["type"] += (
                            tool_call_chunk.type
                            if tool_call_chunk.type
                            and tool_call_chunk.type != tool_calls[tool_call_chunk.index]["type"]
                            else ""
                        )
                        tool_calls[tool_call_chunk.index]["name"] += tool_call_chunk.function.name or ""
                        tool_calls[tool_call_chunk.index]["arguments"] += tool_call_chunk.function.arguments or ""

                if usage := getattr(item, "usage", None):
                    provider_calculated_usage = usage

            total_tokens = input_tokens + output_tokens

            if provider_calculated_usage:
                input_tokens = provider_calculated_usage.prompt_tokens
                output_tokens = provider_calculated_usage.completion_tokens
                total_tokens = provider_calculated_usage.total_tokens

            if tool_calls:
                yield {"tool_calls": tool_calls}

            total_time = time.perf_counter() - start_time

            yield {
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }
            }

            record_metric(
                metric=LLMMetric.INPUT_TOKENS,
                value=input_tokens,
                metric_type=MetricType.HISTOGRAM,
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )
            record_metric(
                metric=LLMMetric.TOKEN_THROUGHPUT,
                value=output_tokens / total_time,
                metric_type=MetricType.HISTOGRAM,
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )
            record_metric(
                metric=LLMMetric.PROMPT_THROUGHPUT,
                value=total_time,
                metric_type=MetricType.HISTOGRAM,
                model=self.model_name,
                prompt=prompt.__class__.__name__,
            )

        return response_to_async_generator(response)  # type: ignore

    def _create_router_from_self_and_options(self, options: LiteLLMOptions) -> "Router":
        params: dict[str, Any] = {
            "model": self.model_name,
            "api_key": self.api_key,
            "api_version": self.api_version,
            "base_url": self.api_base,
        }

        if options.tpm:
            params["tpm"] = options.tpm
        if options.rpm:
            params["rpm"] = options.rpm

        return self._litellm.Router(
            model_list=[{"model_name": self.model_name, "litellm_params": params}],
            routing_strategy="usage-based-routing-v2",
            enable_pre_call_checks=True,
        )

    async def _get_litellm_response(
        self,
        conversation: ChatFormat,
        options: LiteLLMOptions,
        response_format: type[BaseModel] | dict | None,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
        stream: bool = False,
        stream_options: dict | None = None,
    ) -> "ModelResponse | CustomStreamWrapper":
        # Use provided router, or create/reuse cached router
        if self.router:
            entrypoint = self.router
        else:
            # Create router only once and cache it to avoid callback leak
            if self._cached_router is None:
                self._cached_router = self._create_router_from_self_and_options(options)
            entrypoint = self._cached_router

        # Preprocess messages for Claude with reasoning enabled
        processed_conversation = self._preprocess_messages_for_claude(conversation, options)

        # Prepare kwargs for the completion call
        completion_kwargs = {
            "messages": processed_conversation,
            "model": self.model_name,
            "response_format": response_format,
            "tools": tools,
            "tool_choice": tool_choice,
            "stream": stream,
            **options.dict(),
        }

        supported_openai_params = self._litellm.get_supported_openai_params(model=self.model_name) or []
        if "reasoning_effort" not in supported_openai_params:
            completion_kwargs.pop("reasoning_effort")
        if "thinking" not in supported_openai_params:
            completion_kwargs.pop("thinking")

        if stream_options is not None:
            completion_kwargs["stream_options"] = stream_options

        try:
            response = await entrypoint.acompletion(**completion_kwargs)
        except self._litellm.openai.APIConnectionError as exc:
            raise LLMConnectionError() from exc
        except self._litellm.openai.APIStatusError as exc:
            raise LLMStatusError(exc.message, exc.status_code) from exc
        except self._litellm.openai.APIResponseValidationError as exc:
            raise LLMResponseError() from exc
        return response

    def _preprocess_messages_for_claude(self, conversation: ChatFormat, options: LiteLLMOptions) -> ChatFormat:
        """
        Preprocess messages for Claude when reasoning is enabled.

        Claude + reasoning_effort + tool calls creates a conflict:
        - LiteLLM validates messages against OpenAI format (rejects Claude native format)
        - Claude requires thinking blocks when reasoning_effort is set (rejects OpenAI format)

        Subject to removal after the following are resolved on LiteLLM's side:
        Issue: https://github.com/BerriAI/litellm/issues/14194
        Linked PR(s): https://github.com/BerriAI/litellm/pull/15220

        Solution: Summarize tool call history and append to last user message.
        This provides context to Claude without triggering validation errors.

        Args:
            conversation: The conversation in OpenAI format
            options: LLM options including reasoning_effort

        Returns:
            Processed conversation with tool context included
        """

        def create_enhanced_user_message(
            tool_summary_parts: list[str], original_user_msg: str | None
        ) -> dict[str, Any]:
            if tool_summary_parts and original_user_msg:
                enhanced_message = original_user_msg
                enhanced_message += "\n\n[Previous tool calls in this conversation:"

                for summary in tool_summary_parts:
                    enhanced_message += f"\n- {summary}"
                enhanced_message += "\nUse this information to provide your final answer.]"
                return {"role": "user", "content": enhanced_message}

            return {"role": "user", "content": original_user_msg}

        # Only process for Claude models with reasoning enabled
        is_claude = "anthropic" in self.model_name.lower() or "claude" in self.model_name.lower()
        has_reasoning = options.reasoning_effort is not NOT_GIVEN and options.reasoning_effort is not None

        if not (is_claude and has_reasoning):
            return conversation

        # Check if conversation has tool calls
        has_tool_calls = any(msg.get("role") == "assistant" and msg.get("tool_calls") for msg in conversation)

        if not has_tool_calls:
            # No tool calls, conversation is fine as-is
            return conversation

        # Build tool call summary from conversation history
        tool_summary_parts = []
        i = 0
        while i < len(conversation):
            msg = conversation[i]
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Found assistant message with tool calls
                for tool_call in msg["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]
                    tool_id = tool_call["id"]

                    # Find corresponding tool result
                    tool_result = None
                    for j in range(i + 1, len(conversation)):
                        if conversation[j].get("role") == "tool" and conversation[j].get("tool_call_id") == tool_id:
                            tool_result = conversation[j].get("content")
                            break

                    if tool_result:
                        tool_summary_parts.append(f"{tool_name}({tool_args}) returned: {tool_result}")
            i += 1

        # Build processed conversation
        processed = []

        # Keep system message if present
        for msg in conversation:
            if msg.get("role") == "system":
                processed.append(msg)
                break

        # Get the original user message (first non-system)
        original_user_msg = None
        for msg in conversation:
            if msg.get("role") == "user":
                original_user_msg = msg.get("content", "")
                break

        # Create enhanced user message with tool context
        processed.append(create_enhanced_user_message(tool_summary_parts, original_user_msg))

        return processed

    def _get_response_format(
        self, output_schema: type[BaseModel] | dict | None, json_mode: bool
    ) -> type[BaseModel] | dict | None:
        supported_params = self._litellm.get_supported_openai_params(model=self.model_name)

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
            router = cls._get_litellm_module().Router(model_list=config["router"])
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
