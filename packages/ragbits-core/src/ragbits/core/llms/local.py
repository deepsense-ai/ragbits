import asyncio
import threading
from collections.abc import AsyncGenerator

from pydantic import BaseModel

try:
    import accelerate  # noqa: F401
    import torch  # noqa: F401
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer  # noqa: F401

    HAS_LOCAL_LLM = True
except ImportError:
    HAS_LOCAL_LLM = False

from ragbits.core.llms.base import LLM
from ragbits.core.options import Options
from ragbits.core.prompt import ChatFormat
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
        conversation: ChatFormat,
        options: LocalLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> dict:
        """
        Makes a call to the local LLM with the provided prompt and options.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format (not used).
            output_schema: Output schema for requesting a specific response format (not used).

        Returns:
            Response string from LLM.
        """
        input_ids = self.tokenizer.apply_chat_template(
            conversation, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)

        outputs = self.model.generate(
            input_ids,
            eos_token_id=self.tokenizer.eos_token_id,
            **options.dict(),
        )
        response = outputs[0][input_ids.shape[-1] :]
        decoded_response = self.tokenizer.decode(response, skip_special_tokens=True)
        return {"response": decoded_response}

    async def _call_streaming(
        self,
        conversation: ChatFormat,
        options: LocalLLMOptions,
        json_mode: bool = False,
        output_schema: type[BaseModel] | dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Makes a call to the local LLM with the provided prompt and options in streaming manner.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format (not used).
            output_schema: Output schema for requesting a specific response format (not used).

        Returns:
            Async generator of tokens
        """
        input_ids = self.tokenizer.apply_chat_template(
            conversation, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(streamer=streamer, **options.dict())
        generation_thread = threading.Thread(target=self.model.generate, args=(input_ids,), kwargs=generation_kwargs)

        async def streamer_to_async_generator(
            streamer: TextIteratorStreamer, generation_thread: threading.Thread
        ) -> AsyncGenerator[str, None]:
            generation_thread.start()
            for text_piece in streamer:
                yield text_piece
                await asyncio.sleep(0.0)
            generation_thread.join()

        return streamer_to_async_generator(streamer=streamer, generation_thread=generation_thread)
