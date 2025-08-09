import asyncio
import threading
import time
from collections.abc import AsyncGenerator, Iterable
from typing import TYPE_CHECKING, Any

from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.llms.base import LLM, LLMOptions, ToolChoice
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.types import NOT_GIVEN, NotGiven

if TYPE_CHECKING:
    from transformers import TextIteratorStreamer


class LocalLLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the local LLM client.
    Each of them is described in the [HuggingFace documentation]
    (https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client#huggingface_hub.InferenceClient.text_generation).
    """  # noqa: E501

    repetition_penalty: float | None | NotGiven = NOT_GIVEN
    do_sample: bool | None | NotGiven = NOT_GIVEN
    best_of: int | None | NotGiven = NOT_GIVEN
    max_new_tokens: int | None | NotGiven = NOT_GIVEN
    top_k: int | None | NotGiven = NOT_GIVEN
    top_p: float | None | NotGiven = NOT_GIVEN
    seed: int | None | NotGiven = NOT_GIVEN
    stop_sequences: list[str] | None | NotGiven = NOT_GIVEN
    temperature: float | None | NotGiven = NOT_GIVEN


class LocalLLM(LLM[LocalLLMOptions]):
    """
    Class for interaction with any LLM available in HuggingFace.

    Note: Local implementation is not dedicated for production. Use it only in experiments / evaluation
    """

    options_cls = LocalLLMOptions

    def __init__(
        self,
        model_name: str,
        default_options: LocalLLMOptions | None = None,
        *,
        api_key: str | None = None,
        price_per_prompt_token: float = 0.0,
        price_per_completion_token: float = 0.0,
    ) -> None:
        """
        Constructs a new local LLM instance.

        Args:
            model_name: Name of the model to use. This should be a model from the CausalLM class.
            default_options: Default options for the LLM.
            api_key: The API key for Hugging Face authentication.
            price_per_prompt_token: The price per prompt token.
            price_per_completion_token: The price per completion token.

        Raises:
            ImportError: If the 'local' extra requirements are not installed.
            ValueError: If the model was not trained as a chat model.
        """
        deps = self._lazy_import_local_deps()
        if deps is None:
            raise ImportError("You need to install the 'local' extra requirements to use local LLM models")
        torch, AutoModelForCausalLM, AutoTokenizer, self.TextIteratorStreamer = deps

        super().__init__(model_name, default_options)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, device_map="auto", torch_dtype=torch.bfloat16, token=api_key
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=api_key)
        try:
            self.tokenizer.get_chat_template()
        except ValueError as e:
            raise ValueError(
                f"{model_name} was not trained as a chat model - it doesn't support chat template. Select another model"
            ) from e
        self.api_key = api_key
        self._price_per_prompt_token = price_per_prompt_token
        self._price_per_completion_token = price_per_completion_token

    @staticmethod
    def _lazy_import_local_deps() -> tuple[Any, Any, Any, Any] | None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

            return torch, AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
        except ImportError:
            return None

    def get_model_id(self) -> str:
        """
        Returns the model id.
        """
        return "local:" + self.model_name

    def get_estimated_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Returns the estimated cost of the LLM call.
        """
        return self._price_per_prompt_token * prompt_tokens + self._price_per_completion_token * completion_tokens

    def count_tokens(self, prompt: BasePrompt) -> int:
        """
        Counts tokens in the messages.

        Args:
            prompt: Messages to count tokens for.

        Returns:
            Number of tokens in the messages.
        """
        input_ids = self.tokenizer.apply_chat_template(prompt.chat)
        return len(input_ids)

    async def _call(
        self,
        prompt: Iterable[BasePrompt],
        options: LocalLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> list[dict]:
        """
        Makes a call to the local LLM with the provided prompt and options.

        Args:
            prompt:  Iterable of BasePrompt objects containing conversations
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by LLM (Not Supported by the local model).
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools

        Returns:
            Dictionary containing the responses from the LLM and throughput.

        Raises:
            NotImplementedError: If tools are provided.
        """
        if tools or tool_choice:
            raise NotImplementedError("Tools are not supported for local LLMs")

        prompts = [p.chat for p in prompt]

        tokenized = self.tokenizer.apply_chat_template(
            prompts, add_generation_prompt=True, padding=True, return_tensors="pt", return_dict=True
        ).to(self.model.device)
        inputs_ids, attention_mask = tokenized["input_ids"], tokenized["attention_mask"]

        start_time = time.perf_counter()
        outputs = self.model.generate(
            inputs_ids,
            eos_token_id=self.tokenizer.eos_token_id,
            **options.dict(),
        )

        responses = [output[inputs_ids.shape[1] :] for output in outputs]

        results = []
        throughput_batch = time.perf_counter() - start_time
        tokens_in = attention_mask.sum(axis=1).tolist()
        for i, response in enumerate(responses):
            result = {}
            result["response"] = self.tokenizer.decode(response, skip_special_tokens=True)
            result["reasoning"] = None
            prompt_tokens = tokens_in[i]
            completion_tokens = sum(response != self.tokenizer._pad_token_type_id)
            result["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            result["throughput"] = throughput_batch / float(len(responses))
            results.append(result)  # type: ignore

        return results

    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: LocalLLMOptions,
        tools: list[dict] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Makes a call to the local LLM with the provided prompt and options in streaming manner.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            tools: Functions to be used as tools by LLM (not used).
            tool_choice: Parameter that allows to control what tool is used. Can be one of:
                - "auto": let model decide if tool call is needed
                - "none": do not call tool
                - "required: enforce tool usage (model decides which one)
                - dict: tool dict corresponding to one of provided tools

        Returns:
            Async generator of tokens.

        Raises:
            NotImplementedError: If tools are provided.
        """
        if tools or tool_choice:
            raise NotImplementedError("Tools are not supported for local LLMs")

        start_time = time.perf_counter()
        input_tokens = len(
            self.tokenizer.apply_chat_template(prompt.chat, add_generation_prompt=True, return_tensors="pt")[0]
        )
        input_ids = self.tokenizer.apply_chat_template(prompt.chat, add_generation_prompt=True, return_tensors="pt").to(
            self.model.device
        )
        streamer = self.TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(streamer=streamer, **options.dict())
        generation_thread = threading.Thread(target=self.model.generate, args=(input_ids,), kwargs=generation_kwargs)

        async def streamer_to_async_generator(
            streamer: TextIteratorStreamer, generation_thread: threading.Thread
        ) -> AsyncGenerator[dict, None]:
            output_tokens = 0
            generation_thread.start()
            for text in streamer:  # type: ignore[attr-defined]
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
                await asyncio.sleep(0.0)

            generation_thread.join()
            total_time = time.perf_counter() - start_time

            yield {
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
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
                metric=LLMMetric.PROMPT_THROUGHPUT,
                value=total_time,
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

        return streamer_to_async_generator(streamer=streamer, generation_thread=generation_thread)


def __getattr__(name: str) -> type:
    """Allow access to transformers classes for testing purposes."""
    if name in ("AutoModelForCausalLM", "AutoTokenizer", "TextIteratorStreamer"):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

            transformers_classes = {
                "AutoModelForCausalLM": AutoModelForCausalLM,
                "AutoTokenizer": AutoTokenizer,
                "TextIteratorStreamer": TextIteratorStreamer,
            }
            return transformers_classes[name]
        except ImportError:
            pass
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
