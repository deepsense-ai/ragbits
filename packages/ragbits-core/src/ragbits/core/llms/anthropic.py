from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator, MutableSequence
from typing import Any

import httpx

from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.llms.base import LLM, LLMOptions, ToolChoice
from ragbits.core.llms.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMResponseError,
    LLMStatusError,
)
from ragbits.core.llms.pricing import estimate_llm_cost_usd
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.types import NOT_GIVEN, NotGiven

try:
    import anthropic
    from anthropic import AsyncAnthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

_DEFAULT_MAX_TOKENS = 8192


class AnthropicLLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the Anthropic client.
    Each of them is described in the [Anthropic API documentation](https://docs.anthropic.com/en/api/messages).
    """

    temperature: float | None | NotGiven = NOT_GIVEN
    top_p: float | None | NotGiven = NOT_GIVEN
    top_k: int | None | NotGiven = NOT_GIVEN
    stop_sequences: list[str] | None | NotGiven = NOT_GIVEN
    thinking: dict | None | NotGiven = NOT_GIVEN


class AnthropicLLM(LLM[AnthropicLLMOptions]):
    """
    LLM client using the Anthropic Messages API directly.
    """

    options_cls = AnthropicLLMOptions

    def __init__(
        self,
        model_name: str = "claude-haiku-4-5-20251001",
        default_options: AnthropicLLMOptions | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """
        Constructs a new AnthropicLLM instance.

        Args:
            model_name: Name of the Anthropic model to use. Default is "claude-haiku-4-5-20251001".
            default_options: Default options to be used.
            api_key: Anthropic API key. If not specified, reads from the ANTHROPIC_API_KEY environment variable.
            base_url: Custom API base URL.

        Raises:
            ImportError: If the 'anthropic' package is not installed.
        """
        if not HAS_ANTHROPIC:
            raise ImportError(
                "You need to install the 'anthropic' package to use AnthropicLLM."
                " Please install ragbits-core with the 'anthropic' extra: pip install ragbits-core[anthropic]"
            )
        super().__init__(model_name, default_options)
        self.api_key = api_key
        self.base_url = base_url
        self._client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    def get_model_id(self) -> str:
        """
        Returns the model id.
        """
        return "anthropic:" + self.model_name

    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:  # noqa: PLR6301
        """
        Returns an estimated USD cost from token counts using public list prices.

        Unknown ``model_name`` values yield ``0.0``. Bedrock, Vertex, batch, caching,
        and residency pricing are not modeled.
        """
        return estimate_llm_cost_usd("anthropic", self.model_name, prompt_tokens, completion_tokens)

    @staticmethod
    def _convert_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:  # noqa: PLR0912, PLR0915
        """
        Converts OpenAI-format messages to Anthropic format.

        System messages are extracted and concatenated separately. Tool call/result
        messages are converted to Anthropic's content block format.

        Args:
            messages: List of messages in OpenAI chat format.

        Returns:
            Tuple of (system_prompt, anthropic_messages).
        """
        system_parts: list[str] = []
        anthropic_messages: list[dict] = []
        i = 0

        while i < len(messages):
            msg = messages[i]
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                if isinstance(content, str):
                    system_parts.append(content)
                i += 1
                continue

            if role == "user":
                if isinstance(content, str):
                    anthropic_messages.append({"role": "user", "content": content})
                elif isinstance(content, list):
                    parts = []
                    for part in content:
                        if part.get("type") == "text":
                            parts.append({"type": "text", "text": part["text"]})
                        elif part.get("type") == "image_url":
                            image_url = part["image_url"]["url"]
                            if image_url.startswith("data:"):
                                media_type, _, data = image_url.partition(";base64,")
                                media_type = media_type.removeprefix("data:")
                                parts.append(
                                    {
                                        "type": "image",
                                        "source": {"type": "base64", "media_type": media_type, "data": data},
                                    }
                                )
                            else:
                                parts.append(
                                    {
                                        "type": "image",
                                        "source": {"type": "url", "url": image_url},
                                    }
                                )
                    anthropic_messages.append({"role": "user", "content": parts})
                i += 1
                continue

            if role == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    assistant_parts: list[dict] = []
                    if content:
                        assistant_parts.append({"type": "text", "text": content})
                    for tc in tool_calls:
                        assistant_parts.append(
                            {
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["function"]["name"],
                                "input": json.loads(tc["function"]["arguments"]),
                            }
                        )
                    anthropic_messages.append({"role": "assistant", "content": assistant_parts})
                else:
                    anthropic_messages.append({"role": "assistant", "content": content or ""})
                i += 1
                continue

            if role == "tool":
                # Group consecutive tool messages into a single user message.
                tool_results: list[dict] = []
                while i < len(messages) and messages[i].get("role") == "tool":
                    tool_msg = messages[i]
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_msg.get("tool_call_id", ""),
                            "content": tool_msg.get("content", ""),
                        }
                    )
                    i += 1
                anthropic_messages.append({"role": "user", "content": tool_results})
                continue

            i += 1

        system = "\n\n".join(system_parts) if system_parts else None
        return system, anthropic_messages

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[dict]:
        """
        Converts OpenAI-format tool definitions to Anthropic format.

        Args:
            tools: Tool definitions in OpenAI function-calling format.

        Returns:
            Tool definitions in Anthropic format.
        """
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"].get("description", ""),
                "input_schema": tool["function"].get("parameters", {"type": "object", "properties": {}}),
            }
            for tool in tools
        ]

    def _build_create_kwargs(
        self,
        conversation: list[dict],
        system: str | None,
        options: AnthropicLLMOptions,
        tools: list[dict] | None,
        tool_choice: ToolChoice | None,
        stream: bool = False,
    ) -> dict[str, Any]:
        options_dict = {k: v for k, v in options.dict().items() if v is not None}
        max_tokens = options_dict.pop("max_tokens", _DEFAULT_MAX_TOKENS) or _DEFAULT_MAX_TOKENS

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": conversation,
            "max_tokens": max_tokens,
            "stream": stream,
            **options_dict,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        if tool_choice is not None:
            if tool_choice == "auto":
                kwargs["tool_choice"] = {"type": "auto"}
            elif tool_choice == "none":
                kwargs.pop("tools", None)
            elif tool_choice == "required":
                kwargs["tool_choice"] = {"type": "any"}
            elif isinstance(tool_choice, dict) and "function" in tool_choice:
                kwargs["tool_choice"] = {"type": "tool", "name": tool_choice["function"]["name"]}
        return kwargs

    async def _call(
        self,
        prompt: MutableSequence[BasePrompt],
        options: AnthropicLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Calls the Anthropic messages API for all prompts concurrently.

        Args:
            prompt: Batch of prompts to process.
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that controls which tool is used.

        Returns:
            List of response dicts from the LLM.

        Raises:
            LLMConnectionError: If there is a connection error with the API.
            LLMStatusError: If the API returns an error status code.
            LLMResponseError: If the API response is invalid.
            LLMEmptyResponseError: If the API returns an empty response.
        """
        start_time = time.perf_counter()

        async def call_single(p: BasePrompt) -> Any:  # noqa: ANN401
            system, conversation = self._convert_messages(p.chat)
            kwargs = self._build_create_kwargs(conversation, system, options, tools, tool_choice)
            try:
                return await self._client.messages.create(**kwargs)
            except httpx.HTTPStatusError as exc:
                raise LLMStatusError(str(exc), exc.response.status_code) from exc
            except httpx.HTTPError as exc:
                raise LLMConnectionError() from exc
            except anthropic.APIConnectionError as exc:
                raise LLMConnectionError() from exc
            except anthropic.APIStatusError as exc:
                raise LLMStatusError(exc.message, exc.status_code) from exc
            except anthropic.APIResponseValidationError as exc:
                raise LLMResponseError() from exc

        raw_responses = await asyncio.gather(*(call_single(p) for p in prompt))

        results: list[dict] = []
        throughput_batch = time.perf_counter() - start_time

        for response in raw_responses:
            if not response.content:
                raise LLMEmptyResponseError()

            result: dict[str, Any] = {}
            result["throughput"] = throughput_batch / len(raw_responses)

            text_parts = []
            thinking_parts = []
            tool_use_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "thinking":
                    thinking_parts.append(block.thinking)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            result["response"] = "".join(text_parts) or None
            result["reasoning"] = "".join(thinking_parts) or None

            if tools and tool_use_blocks:
                result["tool_calls"] = [
                    {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                        "type": "function",
                        "id": block.id,
                    }
                    for block in tool_use_blocks
                ]

            if response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            results.append(result)

        return results

    async def _call_streaming(  # noqa: PLR0915
        self,
        prompt: BasePrompt,
        options: AnthropicLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Calls the Anthropic messages API with streaming enabled.

        Args:
            prompt: The prompt to process.
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by the LLM.
            tool_choice: Parameter that controls which tool is used.

        Returns:
            Async generator of response chunk dicts.

        Raises:
            LLMConnectionError: If there is a connection error with the API.
            LLMStatusError: If the API returns an error status code.
            LLMResponseError: If the API response is invalid.
        """
        system, conversation = self._convert_messages(prompt.chat)
        kwargs = self._build_create_kwargs(conversation, system, options, tools, tool_choice, stream=True)

        start_time = time.perf_counter()

        try:
            stream = await self._client.messages.create(**kwargs)
        except httpx.HTTPStatusError as exc:
            raise LLMStatusError(str(exc), exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError() from exc
        except anthropic.APIConnectionError as exc:
            raise LLMConnectionError() from exc
        except anthropic.APIStatusError as exc:
            raise LLMStatusError(exc.message, exc.status_code) from exc
        except anthropic.APIResponseValidationError as exc:
            raise LLMResponseError() from exc

        async def generate() -> AsyncGenerator[dict, None]:  # noqa: PLR0912
            output_tokens = 0
            input_tokens = 0
            # track in-progress tool use blocks: index -> {id, name, input_json}
            tool_blocks: dict[int, dict[str, str]] = {}
            current_block_index = -1
            current_block_type = ""

            async for event in stream:
                event_type = event.type

                if event_type == "content_block_start":
                    current_block_index = event.index
                    current_block_type = event.content_block.type
                    if current_block_type == "tool_use":
                        tool_blocks[current_block_index] = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "arguments": "",
                        }

                elif event_type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        text = delta.text
                        if text:
                            output_tokens += 1
                            if output_tokens == 1:
                                record_metric(
                                    metric=LLMMetric.TIME_TO_FIRST_TOKEN,
                                    value=time.perf_counter() - start_time,
                                    metric_type=MetricType.HISTOGRAM,
                                    model=self.model_name,
                                    prompt=prompt.__class__.__name__,
                                )
                            yield {"response": text, "reasoning": False}
                    elif delta.type == "thinking_delta":
                        thinking = delta.thinking
                        if thinking:
                            output_tokens += 1
                            yield {"response": thinking, "reasoning": True}
                    elif delta.type == "input_json_delta":
                        if current_block_index in tool_blocks:
                            tool_blocks[current_block_index]["arguments"] += delta.partial_json

                elif event_type == "message_delta":
                    if hasattr(event, "usage") and event.usage:
                        output_tokens = event.usage.output_tokens

                elif event_type == "message_start":
                    if hasattr(event, "message") and event.message.usage:
                        input_tokens = event.message.usage.input_tokens

            if tool_blocks:
                yield {
                    "tool_calls": [
                        {
                            "id": block["id"],
                            "name": block["name"],
                            "arguments": block["arguments"],
                            "type": "function",
                        }
                        for block in tool_blocks.values()
                    ]
                }

            total_time = time.perf_counter() - start_time
            total_tokens = input_tokens + output_tokens

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
                value=output_tokens / total_time if total_time > 0 else 0,
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

        return generate()
