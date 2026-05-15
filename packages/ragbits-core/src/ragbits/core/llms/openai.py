from __future__ import annotations

import asyncio
import base64
import time
from collections.abc import AsyncGenerator, MutableSequence
from copy import deepcopy
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import tiktoken as tiktoken_stubs
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

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
from ragbits.core.utils.chat_message_text import iter_text_segments_from_openai_message_content

try:
    import openai
    from openai import AsyncOpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import tiktoken

    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class OpenAILLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the OpenAI client.
    Each of them is described in the
    [OpenAI API documentation](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
    """

    frequency_penalty: float | None | NotGiven = NOT_GIVEN
    n: int | None | NotGiven = NOT_GIVEN
    presence_penalty: float | None | NotGiven = NOT_GIVEN
    seed: int | None | NotGiven = NOT_GIVEN
    stop: str | list[str] | None | NotGiven = NOT_GIVEN
    logprobs: bool | None | NotGiven = NOT_GIVEN
    top_logprobs: int | None | NotGiven = NOT_GIVEN
    logit_bias: dict | None | NotGiven = NOT_GIVEN
    reasoning_effort: Literal["low", "medium", "high"] | None | NotGiven = NOT_GIVEN


class OpenAILLM(LLM[OpenAILLMOptions]):
    """
    LLM client using the OpenAI Chat Completions API directly.
    """

    options_cls = OpenAILLMOptions

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        default_options: OpenAILLMOptions | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        use_structured_output: bool = False,
    ) -> None:
        """
        Constructs a new OpenAILLM instance.

        Args:
            model_name: Name of the OpenAI model to use. Default is "gpt-4o-mini".
            default_options: Default options to be used.
            api_key: OpenAI API key. If not specified, reads from the OPENAI_API_KEY environment variable.
            base_url: Custom API base URL for compatible APIs (e.g. Azure OpenAI, local servers).
            use_structured_output: Whether to request structured output from the model when an output schema
                is provided by the prompt. Default is False.

        Raises:
            ImportError: If the 'openai' package is not installed.
        """
        if not HAS_OPENAI:
            raise ImportError(
                "You need to install the 'openai' package to use OpenAILLM."
                " Please install ragbits-core with the 'openai' extra: pip install ragbits-core[openai]"
            )
        super().__init__(model_name, default_options)
        self.api_key = api_key
        self.base_url = base_url
        self.use_structured_output = use_structured_output
        # Local servers (e.g. Ollama) don't require a real API key, but AsyncOpenAI
        # raises if api_key is None and OPENAI_API_KEY is not set. Use a placeholder
        # so that custom base_url targets work without setting any environment variable.
        effective_api_key = api_key if api_key is not None else ("local" if base_url is not None else None)
        self._client = AsyncOpenAI(api_key=effective_api_key, base_url=base_url)

    def get_model_id(self) -> str:
        """
        Returns the model id.
        """
        return "openai:" + self.model_name

    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:  # noqa: PLR6301
        """
        Returns an estimated USD cost from token counts using public list prices.

        Unknown or custom ``model_name`` values yield ``0.0``. Actual invoices may
        differ (discounts, batch, caching, negotiated rates).
        """
        return estimate_llm_cost_usd("openai", self.model_name, prompt_tokens, completion_tokens)

    def count_tokens(self, prompt: BasePrompt) -> int:
        """
        Counts tokens in the prompt using tiktoken when available.

        Unknown OpenAI-compatible model names fall back to ``o200k_base`` then
        ``cl100k_base``. If tiktoken is unavailable, uses a rough ``~4 chars``
        per token estimate (never raw character count, which is far too high).

        Args:
            prompt: Formatted prompt template with conversation.

        Returns:
            Approximate token count.
        """
        if HAS_TIKTOKEN:
            enc = self._tiktoken_encoding()
            if enc is not None:
                return sum(
                    len(enc.encode(segment))
                    for msg in prompt.chat
                    for segment in iter_text_segments_from_openai_message_content(msg.get("content"))
                )
        return sum(
            self._approx_tokens_no_tiktoken(segment)
            for msg in prompt.chat
            for segment in iter_text_segments_from_openai_message_content(msg.get("content"))
        )

    def _tiktoken_encoding(self) -> tiktoken_stubs.Encoding | None:
        if not HAS_TIKTOKEN:
            return None
        try:
            return tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            for name in ("o200k_base", "cl100k_base"):
                try:
                    return tiktoken.get_encoding(name)
                except KeyError:
                    continue
        return None

    @staticmethod
    def _approx_tokens_no_tiktoken(text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def _to_json_schema_response_format(output_schema: type[BaseModel] | dict) -> dict:
        if isinstance(output_schema, dict):
            if output_schema.get("type") in {"json_object", "json_schema", "text"}:
                return output_schema
            return {
                "type": "json_schema",
                "json_schema": {"name": output_schema.get("title", "response"), "schema": output_schema},
            }
        return {
            "type": "json_schema",
            "json_schema": {"name": output_schema.__name__, "schema": output_schema.model_json_schema()},
        }

    def _get_response_format(self, output_schema: type[BaseModel] | dict | None, json_mode: bool) -> dict | None:
        if output_schema is not None and self.use_structured_output:
            return self._to_json_schema_response_format(output_schema)
        if json_mode:
            return {"type": "json_object"}
        return None

    @staticmethod
    def _is_url(value: str) -> bool:
        return value.startswith("https://") or value.startswith("http://") or value.startswith("www.")

    @staticmethod
    def _filename_from_url(url: str) -> str:
        path = PurePosixPath(urlparse(url).path)
        return path.name or "attachment.pdf"

    @staticmethod
    def _decode_file_data(file_data: str) -> bytes:
        if file_data.startswith("data:") and ";base64," in file_data:
            _, _, encoded = file_data.partition(";base64,")
            return base64.b64decode(encoded)

        try:
            return base64.b64decode(file_data)
        except Exception:
            return file_data.encode("utf-8")

    @staticmethod
    async def _download_url_as_bytes(url: str) -> bytes:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def _upload_pdf_and_get_file_id(self, data: bytes, filename: str) -> str:
        uploaded_file = await self._client.files.create(
            file=(filename, data, "application/pdf"),
            purpose="user_data",
        )
        return uploaded_file.id

    async def _normalize_pdf_attachments(
        self, conversation: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        Normalize PDF attachments for OpenAI chat completions.

        OpenAI chat completions currently requires `file_id` references for PDF inputs.
        This method translates URL-based and inline `file_data` PDFs into temporary uploaded files
        and replaces attachment payloads with `file_id`.
        """
        normalized_conversation = deepcopy(conversation)
        uploaded_file_ids: list[str] = []
        cached_url_uploads: dict[str, str] = {}

        for message in normalized_conversation:
            content = message.get("content")
            if not isinstance(content, list):
                continue

            for item in content:
                if not isinstance(item, dict) or item.get("type") != "file":
                    continue

                file_payload = item.get("file")
                if not isinstance(file_payload, dict):
                    continue

                file_id = file_payload.get("file_id")
                file_data = file_payload.get("file_data")

                if isinstance(file_id, str) and self._is_url(file_id):
                    if file_id not in cached_url_uploads:
                        downloaded_pdf = await self._download_url_as_bytes(file_id)
                        uploaded_id = await self._upload_pdf_and_get_file_id(
                            data=downloaded_pdf,
                            filename=self._filename_from_url(file_id),
                        )
                        cached_url_uploads[file_id] = uploaded_id
                        uploaded_file_ids.append(uploaded_id)

                    item["file"] = {"file_id": cached_url_uploads[file_id]}
                    continue

                if isinstance(file_data, str):
                    uploaded_id = await self._upload_pdf_and_get_file_id(
                        data=self._decode_file_data(file_data),
                        filename=file_payload.get("filename", "attachment.pdf"),
                    )
                    uploaded_file_ids.append(uploaded_id)
                    item["file"] = {"file_id": uploaded_id}

        return normalized_conversation, uploaded_file_ids

    async def _get_openai_response(  # noqa: PLR0912
        self,
        conversation: list[dict],
        options: OpenAILLMOptions,
        response_format: dict | None = None,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
        stream: bool = False,
    ) -> Any:  # noqa: ANN401
        temporary_file_ids: list[str] = []
        response: Any = None
        try:
            normalized_conversation, temporary_file_ids = await self._normalize_pdf_attachments(conversation)
            options_dict = {k: v for k, v in options.dict().items() if v is not None}
            kwargs: dict[str, Any] = {
                "model": self.model_name,
                "messages": normalized_conversation,
                "stream": stream,
                **options_dict,
            }
            if response_format is not None:
                kwargs["response_format"] = response_format
            if tools:
                kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
            if stream:
                kwargs["stream_options"] = {"include_usage": True}

            response = await self._client.chat.completions.create(**kwargs)
            return response
        except httpx.HTTPStatusError as exc:
            raise LLMStatusError(str(exc), exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError() from exc
        except openai.APIConnectionError as exc:
            raise LLMConnectionError() from exc
        except openai.APIStatusError as exc:
            raise LLMStatusError(exc.message, exc.status_code) from exc
        except openai.APIResponseValidationError as exc:
            raise LLMResponseError() from exc
        finally:
            if temporary_file_ids:
                if stream and response is not None:
                    response._ragbits_temp_file_ids = temporary_file_ids
                else:
                    await asyncio.gather(
                        *(self._client.files.delete(file_id) for file_id in temporary_file_ids),
                        return_exceptions=True,
                    )

    async def _call(
        self,
        prompt: MutableSequence[BasePrompt],
        options: OpenAILLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Calls the OpenAI chat completions API for all prompts concurrently.

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
        raw_responses = await asyncio.gather(
            *(
                self._get_openai_response(
                    conversation=p.chat,
                    options=options,
                    response_format=self._get_response_format(
                        output_schema=p.output_schema(),
                        json_mode=p.json_mode,
                    ),
                    tools=tools,
                    tool_choice=tool_choice,
                )
                for p in prompt
            )
        )

        results: list[dict] = []
        throughput_batch = time.perf_counter() - start_time

        for response in raw_responses:
            if not response.choices:
                raise LLMEmptyResponseError()

            result: dict[str, Any] = {}
            result["response"] = response.choices[0].message.content
            result["reasoning"] = getattr(response.choices[0].message, "reasoning_content", None)
            result["throughput"] = throughput_batch / len(raw_responses)

            if tools and (tool_calls := response.choices[0].message.tool_calls):
                result["tool_calls"] = [
                    {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                        "type": tc.type,
                        "id": tc.id,
                    }
                    for tc in tool_calls
                ]

            if options.logprobs:
                result["logprobs"] = response.choices[0].logprobs

            if response.usage:
                result["usage"] = {
                    "completion_tokens": response.usage.completion_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            results.append(result)

        return results

    async def _call_streaming(  # noqa: PLR0915
        self,
        prompt: BasePrompt,
        options: OpenAILLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Calls the OpenAI chat completions API with streaming enabled.

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
        response_format = self._get_response_format(
            output_schema=prompt.output_schema(),
            json_mode=prompt.json_mode,
        )
        input_tokens = self.count_tokens(prompt)
        start_time = time.perf_counter()

        stream = await self._get_openai_response(
            conversation=prompt.chat,
            options=options,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
        )
        temporary_file_ids: list[str] = getattr(stream, "_ragbits_temp_file_ids", [])

        async def generate() -> AsyncGenerator[dict, None]:  # noqa: PLR0912
            nonlocal input_tokens
            output_tokens = 0
            tool_calls_buffer: list[dict] = []
            provider_usage = None

            try:
                async for chunk in stream:
                    if not chunk.choices:
                        if usage := getattr(chunk, "usage", None):
                            provider_usage = usage
                        continue

                    delta = chunk.choices[0].delta
                    reasoning_content = getattr(delta, "reasoning_content", None)

                    if content := delta.content or reasoning_content:
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

                    if tool_call_deltas := delta.tool_calls:
                        for tc_delta in tool_call_deltas:
                            while len(tool_calls_buffer) <= tc_delta.index:
                                tool_calls_buffer.append({"id": "", "type": "", "name": "", "arguments": ""})
                            tool_calls_buffer[tc_delta.index]["id"] += tc_delta.id or ""
                            tool_calls_buffer[tc_delta.index]["type"] += (
                                tc_delta.type
                                if tc_delta.type and tc_delta.type != tool_calls_buffer[tc_delta.index]["type"]
                                else ""
                            )
                            tool_calls_buffer[tc_delta.index]["name"] += tc_delta.function.name or ""
                            tool_calls_buffer[tc_delta.index]["arguments"] += tc_delta.function.arguments or ""

                    if usage := getattr(chunk, "usage", None):
                        provider_usage = usage

                if tool_calls_buffer:
                    yield {"tool_calls": tool_calls_buffer}

                total_time = time.perf_counter() - start_time

                if provider_usage:
                    prompt_tokens = provider_usage.prompt_tokens
                    completion_tokens = provider_usage.completion_tokens
                    total_tokens = provider_usage.total_tokens
                else:
                    prompt_tokens = input_tokens
                    completion_tokens = output_tokens
                    total_tokens = input_tokens + output_tokens

                yield {
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    }
                }

                record_metric(
                    metric=LLMMetric.INPUT_TOKENS,
                    value=prompt_tokens,
                    metric_type=MetricType.HISTOGRAM,
                    model=self.model_name,
                    prompt=prompt.__class__.__name__,
                )
                record_metric(
                    metric=LLMMetric.TOKEN_THROUGHPUT,
                    value=completion_tokens / total_time if total_time > 0 else 0,
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
            finally:
                if temporary_file_ids:
                    await asyncio.gather(
                        *(self._client.files.delete(file_id) for file_id in temporary_file_ids),
                        return_exceptions=True,
                    )

        return generate()
