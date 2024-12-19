from functools import cached_property

try:
    from transformers import AutoTokenizer

    HAS_LOCAL_LLM = True
except ImportError:
    HAS_LOCAL_LLM = False

from ragbits.core.prompt.base import BasePrompt

from .base import LLM
from .clients.local import LocalLLMClient, LocalLLMOptions


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
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=api_key)
        self.api_key = api_key

    @cached_property
    def client(self) -> LocalLLMClient:
        """
        Client for the LLM.

        Returns:
            The client used to interact with the LLM.
        """
        return LocalLLMClient(model_name=self.model_name, hf_api_key=self.api_key)

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
