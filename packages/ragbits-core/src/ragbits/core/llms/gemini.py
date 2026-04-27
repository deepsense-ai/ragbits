from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator, MutableSequence
from typing import Any

from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.llms.base import LLM, LLMOptions, ToolChoice
from ragbits.core.llms.exceptions import (
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMStatusError,
)
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.types import NOT_GIVEN, NotGiven

try:
    from google import genai
    from google.api_core import exceptions as google_exceptions
    from google.genai import types as genai_types

    HAS_GOOGLE_GENAI = True
except (ImportError, TypeError):
    # TypeError can occur with some google-genai versions on Python < 3.13
    # (TypedDict extra_items feature requires 3.13+).
    HAS_GOOGLE_GENAI = False
    genai = None  # type: ignore[assignment]
    google_exceptions = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]


class GeminiLLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the Gemini client.
    Each of them is described in the [Google AI documentation](https://ai.google.dev/api/generate-content).
    """

    temperature: float | None | NotGiven = NOT_GIVEN
    top_p: float | None | NotGiven = NOT_GIVEN
    top_k: int | None | NotGiven = NOT_GIVEN
    candidate_count: int | None | NotGiven = NOT_GIVEN
    stop_sequences: list[str] | None | NotGiven = NOT_GIVEN
    presence_penalty: float | None | NotGiven = NOT_GIVEN
    frequency_penalty: float | None | NotGiven = NOT_GIVEN


class GeminiLLM(LLM[GeminiLLMOptions]):
    """
    LLM client using the Google Gemini API via the google-genai SDK.
    """

    options_cls = GeminiLLMOptions

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        default_options: GeminiLLMOptions | None = None,
        *,
        api_key: str | None = None,
        project: str | None = None,
        location: str | None = None,
        vertexai: bool = False,
    ) -> None:
        """
        Constructs a new GeminiLLM instance.

        Args:
            model_name: Name of the Gemini model to use. Default is "gemini-2.5-flash".
            default_options: Default options to be used.
            api_key: Google AI API key. If not specified, reads from the GOOGLE_API_KEY environment variable.
                Not used when vertexai=True.
            project: Google Cloud project ID. Used only when vertexai=True.
            location: Google Cloud region. Used only when vertexai=True. Defaults to "us-central1".
            vertexai: Whether to use Vertex AI instead of Google AI Studio. Default is False.

        Raises:
            ImportError: If the 'google-genai' package is not installed.
        """
        if not HAS_GOOGLE_GENAI:
            raise ImportError(
                "You need to install the 'google-genai' package to use GeminiLLM."
                " Please install ragbits-core with the 'gemini' extra: pip install ragbits-core[gemini]"
            )
        super().__init__(model_name, default_options)
        self.api_key = api_key
        self.project = project
        self.location = location
        self.vertexai = vertexai

        if vertexai:
            self._client = genai.Client(vertexai=True, project=project, location=location or "us-central1")
        else:
            self._client = genai.Client(api_key=api_key)

    def get_model_id(self) -> str:
        """
        Returns the model id.
        """
        return "gemini:" + self.model_name

    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:  # noqa: PLR6301
        """
        Returns 0.0 — cost estimation is not bundled; use the Google Cloud console for billing details.
        """
        return 0.0

    @staticmethod
    def _convert_messages(messages: list[dict]) -> tuple[str | None, list[genai_types.Content]]:  # noqa: PLR0912, PLR0915
        """
        Converts OpenAI-format messages to Gemini Content format.

        System messages are extracted and concatenated separately. Tool calls
        and tool results are converted to Gemini FunctionCall/FunctionResponse parts.

        Args:
            messages: List of messages in OpenAI chat format.

        Returns:
            Tuple of (system_instruction, gemini_contents).
        """
        system_parts: list[str] = []
        contents: list[genai_types.Content] = []
        # Map tool call IDs to function names for tool result conversion.
        tool_call_id_to_name: dict[str, str] = {}

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
                parts: list[genai_types.Part] = []
                if isinstance(content, str):
                    parts.append(genai_types.Part(text=content))
                elif isinstance(content, list):
                    for part in content:
                        if part.get("type") == "text":
                            parts.append(genai_types.Part(text=part["text"]))
                        elif part.get("type") == "image_url":
                            image_url = part["image_url"]["url"]
                            if image_url.startswith("data:"):
                                import base64

                                media_type, _, data = image_url.partition(";base64,")
                                media_type = media_type.removeprefix("data:")
                                parts.append(
                                    genai_types.Part.from_bytes(
                                        data=base64.b64decode(data),
                                        mime_type=media_type,
                                    )
                                )
                            else:
                                parts.append(genai_types.Part(text=f"[Image: {image_url}]"))
                contents.append(genai_types.Content(role="user", parts=parts))
                i += 1
                continue

            if role == "assistant":
                tool_calls = msg.get("tool_calls")
                parts = []
                if content:
                    parts.append(genai_types.Part(text=content))
                if tool_calls:
                    for tc in tool_calls:
                        func_name = tc["function"]["name"]
                        tool_call_id_to_name[tc["id"]] = func_name
                        parts.append(
                            genai_types.Part(
                                function_call=genai_types.FunctionCall(
                                    name=func_name,
                                    args=json.loads(tc["function"]["arguments"]),
                                )
                            )
                        )
                if not parts:
                    parts.append(genai_types.Part(text=""))
                contents.append(genai_types.Content(role="model", parts=parts))
                i += 1
                continue

            if role == "tool":
                # Group consecutive tool messages into a single user message.
                tool_parts: list[genai_types.Part] = []
                while i < len(messages) and messages[i].get("role") == "tool":
                    tool_msg = messages[i]
                    call_id = tool_msg.get("tool_call_id", "")
                    func_name = tool_call_id_to_name.get(call_id, "unknown")
                    tool_parts.append(
                        genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=func_name,
                                response={"result": tool_msg.get("content", "")},
                            )
                        )
                    )
                    i += 1
                contents.append(genai_types.Content(role="user", parts=tool_parts))
                continue

            i += 1

        system = "\n\n".join(system_parts) if system_parts else None
        return system, contents

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[genai_types.Tool]:
        """
        Converts OpenAI-format tool definitions to Gemini FunctionDeclaration format.

        Args:
            tools: Tool definitions in OpenAI function-calling format.

        Returns:
            List of Gemini Tool objects.
        """
        declarations = []
        for tool in tools:
            func = tool["function"]
            params = func.get("parameters")
            declarations.append(
                genai_types.FunctionDeclaration(
                    name=func["name"],
                    description=func.get("description", ""),
                    parameters=genai_types.Schema(**params) if params else None,
                )
            )
        return [genai_types.Tool(function_declarations=declarations)]

    def _build_config(
        self,
        system: str | None,
        options: GeminiLLMOptions,
        tools: list[dict] | None,
        tool_choice: ToolChoice | None,
        response_mime_type: str | None = None,
    ) -> genai_types.GenerateContentConfig:
        options_dict = {k: v for k, v in options.dict().items() if v is not None}
        max_tokens = options_dict.pop("max_tokens", None)

        gemini_tools = self._convert_tools(tools) if tools else None

        tool_config = None
        if tool_choice is not None and tools:
            if tool_choice == "none":
                tool_config = genai_types.ToolConfig(
                    function_calling_config=genai_types.FunctionCallingConfig(
                        mode=genai_types.FunctionCallingConfigMode.NONE
                    )
                )
            elif tool_choice == "required":
                tool_config = genai_types.ToolConfig(
                    function_calling_config=genai_types.FunctionCallingConfig(
                        mode=genai_types.FunctionCallingConfigMode.ANY
                    )
                )
            elif isinstance(tool_choice, dict) and "function" in tool_choice:
                tool_config = genai_types.ToolConfig(
                    function_calling_config=genai_types.FunctionCallingConfig(
                        mode=genai_types.FunctionCallingConfigMode.ANY,
                        allowed_function_names=[tool_choice["function"]["name"]],
                    )
                )

        return genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            tools=gemini_tools,  # type: ignore[arg-type]
            tool_config=tool_config,
            response_mime_type=response_mime_type,
            **options_dict,
        )

    async def _call(
        self,
        prompt: MutableSequence[BasePrompt],
        options: GeminiLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Calls the Gemini generate content API for all prompts concurrently.

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

        async def call_single(p: BasePrompt) -> Any:  # noqa: ANN401
            response_mime_type = "application/json" if p.json_mode else None
            system, contents = self._convert_messages(p.chat)
            config = self._build_config(system, options, tools, tool_choice, response_mime_type)
            try:
                return await self._client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,  # type: ignore[arg-type]
                    config=config,
                )
            except google_exceptions.GoogleAPICallError as exc:
                status_code = exc.code if exc.code is not None else 500
                raise LLMStatusError(str(exc), status_code) from exc
            except google_exceptions.GoogleAPIError as exc:
                raise LLMConnectionError(str(exc)) from exc

        start_time = time.perf_counter()
        raw_responses = await asyncio.gather(*(call_single(p) for p in prompt))

        results: list[dict] = []
        throughput_batch = time.perf_counter() - start_time

        for response in raw_responses:
            if not response.candidates:
                raise LLMEmptyResponseError()

            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise LLMEmptyResponseError()

            result: dict[str, Any] = {}
            result["throughput"] = throughput_batch / len(raw_responses)

            text_parts: list[str] = []
            func_calls: list[dict[str, str]] = []

            for part in candidate.content.parts:
                if part.text:
                    text_parts.append(part.text)
                elif part.function_call:
                    fc = part.function_call
                    func_calls.append(
                        {
                            "name": fc.name,
                            "arguments": json.dumps(dict(fc.args) if fc.args else {}),
                            "type": "function",
                            "id": f"call_{len(func_calls)}",
                        }
                    )

            result["response"] = "".join(text_parts) or None
            result["reasoning"] = None

            if tools and func_calls:
                result["tool_calls"] = func_calls

            if response.usage_metadata:
                result["usage"] = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0,
                }

            results.append(result)

        return results

    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: GeminiLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Calls the Gemini generate content API with streaming enabled.

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
        response_mime_type = "application/json" if prompt.json_mode else None
        system, contents = self._convert_messages(prompt.chat)
        config = self._build_config(system, options, tools, tool_choice, response_mime_type)

        start_time = time.perf_counter()

        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )
        except google_exceptions.GoogleAPICallError as exc:
            status_code = exc.code if exc.code is not None else 500
            raise LLMStatusError(str(exc), status_code) from exc
        except google_exceptions.GoogleAPIError as exc:
            raise LLMConnectionError(str(exc)) from exc

        async def generate() -> AsyncGenerator[dict, None]:
            output_tokens = 0
            input_tokens = 0
            func_calls: list[dict] = []

            async for chunk in stream:
                if not chunk.candidates:
                    if chunk.usage_metadata:
                        input_tokens = chunk.usage_metadata.prompt_token_count or 0
                        output_tokens = chunk.usage_metadata.candidates_token_count or 0
                    continue

                candidate = chunk.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            output_tokens += 1
                            if output_tokens == 1:
                                record_metric(
                                    metric=LLMMetric.TIME_TO_FIRST_TOKEN,
                                    value=time.perf_counter() - start_time,
                                    metric_type=MetricType.HISTOGRAM,
                                    model=self.model_name,
                                    prompt=prompt.__class__.__name__,
                                )
                            yield {"response": part.text, "reasoning": False}
                        elif part.function_call:
                            fc = part.function_call
                            func_calls.append(
                                {
                                    "name": fc.name,
                                    "arguments": json.dumps(dict(fc.args) if fc.args else {}),
                                    "type": "function",
                                    "id": f"call_{len(func_calls)}",
                                }
                            )

                if chunk.usage_metadata:
                    input_tokens = chunk.usage_metadata.prompt_token_count or input_tokens
                    output_tokens = chunk.usage_metadata.candidates_token_count or output_tokens

            if func_calls:
                yield {"tool_calls": func_calls}

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
