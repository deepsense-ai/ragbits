from dataclasses import dataclass
from typing import Dict, List, Optional, Type, Union

from pydantic import BaseModel

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    HAS_LOCAL_LLM = True
except ImportError:
    HAS_LOCAL_LLM = False

from ragstack_common.prompt import ChatFormat

from ..types import NOT_GIVEN, NotGiven
from .base import LLMClient, LLMOptions


@dataclass
class LocalLLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the local LLM client.
    Each of them is described in the [HuggingFace documentation]
    (https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client#huggingface_hub.InferenceClient.text_generation). # pylint: disable=line-too-long
    """

    repetition_penalty: Union[Optional[float], NotGiven] = NOT_GIVEN
    do_sample: Union[Optional[bool], NotGiven] = NOT_GIVEN
    best_of: Union[Optional[int], NotGiven] = NOT_GIVEN
    max_new_tokens: Union[Optional[int], NotGiven] = NOT_GIVEN
    top_k: Union[Optional[int], NotGiven] = NOT_GIVEN
    top_p: Union[Optional[float], NotGiven] = NOT_GIVEN
    seed: Union[Optional[int], NotGiven] = NOT_GIVEN
    stop_sequences: Union[Optional[List[str]], NotGiven] = NOT_GIVEN
    temperature: Union[Optional[float], NotGiven] = NOT_GIVEN


class LocalLLMClient(LLMClient[LocalLLMOptions]):
    """
    Client for the local LLM that supports Hugging Face models.
    """

    _options_cls = LocalLLMOptions

    def __init__(
        self,
        model_name: str,
        *,
        hf_api_key: Optional[str] = None,
    ) -> None:
        """
        Constructs a new local LLMClient instance.

        Args:
            model_name: Name of the model to use.
            hf_api_key: The Hugging Face API key for authentication.
        """
        if not HAS_LOCAL_LLM:
            raise ImportError("You need to install the 'local' extra requirements to use local LLM models")

        super().__init__(model_name)

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, device_map="auto", torch_dtype=torch.bfloat16, token=hf_api_key
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_api_key)

    async def call(
        self,
        conversation: ChatFormat,
        options: LocalLLMOptions,
        json_mode: bool = False,
        output_schema: Optional[Type[BaseModel] | Dict] = None,
    ) -> str:
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
        return decoded_response
