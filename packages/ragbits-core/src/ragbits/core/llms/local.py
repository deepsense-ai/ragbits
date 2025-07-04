import asyncio
import threading
import time
from collections.abc import AsyncGenerator

from pydantic import BaseModel

try:
    import accelerate  # noqa: F401
    import torch  # noqa: F401
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer  # noqa: F401

    HAS_LOCAL_LLM = True
except ImportError:
    HAS_LOCAL_LLM = False

from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import LLMMetric, MetricType
from ragbits.core.llms.base import LLM
from ragbits.core.options import Options
from ragbits.core.prompt.base import BasePrompt
from ragbits.core.types import NOT_GIVEN, NotGiven


class LocalLLMOptions(Options):
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
    ) -> None:
        """
        Constructs a new local LLM instance.

        Args:
            model_name: Name of the model to use. This should be a model from the CausalLM class.
            default_options: Default options for the LLM.
            api_key: The API key for Hugging Face authentication.

        Raises:
            ImportError: If the 'local' extra requirements are not installed.
        """
        if not HAS_LOCAL_LLM:
            raise ImportError("You need to install the 'local' extra requirements to use local LLM models")

        super().__init__(model_name, default_options)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, device_map="auto", torch_dtype=torch.bfloat16, token=api_key
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=api_key)
        self.api_key = api_key

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
        prompt: BasePrompt,
        options: LocalLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Makes a call to the local LLM with the provided prompt and options.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format (not used).
            output_schema: Output schema for requesting a specific response format (not used).
            tools: Functions to be used as tools by LLM (not used).

        Returns:
            Response string from LLM.
        """
        start_time = time.perf_counter()
        input_ids = self.tokenizer.apply_chat_template(prompt.chat, add_generation_prompt=True, return_tensors="pt").to(
            self.model.device
        )
        outputs = self.model.generate(
            input_ids,
            eos_token_id=self.tokenizer.eos_token_id,
            **options.dict(),
        )
        response = outputs[0][input_ids.shape[-1] :]
        decoded_response = self.tokenizer.decode(response, skip_special_tokens=True)
        prompt_throughput = time.perf_counter() - start_time

        record_metric(
            metric=LLMMetric.INPUT_TOKENS,
            value=input_ids.shape[-1],
            metric_type=MetricType.HISTOGRAM,
            model=self.model_name,
            prompt=prompt.__class__.__name__,
        )
        record_metric(
            metric=LLMMetric.PROMPT_THROUGHPUT,
            value=prompt_throughput,
            metric_type=MetricType.HISTOGRAM,
            model=self.model_name,
            prompt=prompt.__class__.__name__,
        )
        record_metric(
            metric=LLMMetric.TOKEN_THROUGHPUT,
            value=outputs.total_tokens / prompt_throughput,
            metric_type=MetricType.HISTOGRAM,
            model=self.model_name,
            prompt=prompt.__class__.__name__,
        )

        return {"response": decoded_response}

    async def _call_streaming(
        self,
        prompt: BasePrompt,
        options: LocalLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Makes a call to the local LLM with the provided prompt and options in streaming manner.

        Args:
            prompt: Formatted prompt template with conversation.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format (not used).
            output_schema: Output schema for requesting a specific response format (not used).
            tools: Functions to be used as tools by LLM (not used).

        Returns:
            Async generator of tokens
        """
        start_time = time.perf_counter()
        input_tokens = len(
            self.tokenizer.apply_chat_template(prompt.chat, add_generation_prompt=True, return_tensors="pt")[0]
        )
        input_ids = self.tokenizer.apply_chat_template(prompt.chat, add_generation_prompt=True, return_tensors="pt").to(
            self.model.device
        )
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(streamer=streamer, **options.dict())
        generation_thread = threading.Thread(target=self.model.generate, args=(input_ids,), kwargs=generation_kwargs)

        async def streamer_to_async_generator(
            streamer: TextIteratorStreamer, generation_thread: threading.Thread
        ) -> AsyncGenerator[dict, None]:
            output_tokens = 0
            generation_thread.start()
            for text in streamer:
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

                yield {"response": text}
                await asyncio.sleep(0.0)

            generation_thread.join()
            total_time = time.perf_counter() - start_time

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
