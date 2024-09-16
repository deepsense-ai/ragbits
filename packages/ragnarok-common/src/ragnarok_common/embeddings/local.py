from functools import cached_property
from typing import Optional

try:
    from transformers import PreTrainedModel

    HAS_LOCAL_EMBEDDINGS = True
except ImportError:
    HAS_LOCAL_EMBEDDINGS = False

from .base import Embeddings
from .clients.local import LocalEmbeddingsClient, LocalEmbeddingsOptions


class LocalEmbeddings(Embeddings[LocalEmbeddingsOptions]):
    """
    Class for interaction with any encoder available in HuggingFace.
    """

    _options_cls = LocalEmbeddingsOptions

    def __init__(
        self,
        model_name: str,
        default_options: Optional[LocalEmbeddingsOptions] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Constructs a new local LLM instance.

        Args:
            model_name: Name of the model to use.
            default_options: Default options to be used.
            api_key: The API key for Hugging Face authentication.
        """
        if not HAS_LOCAL_EMBEDDINGS:
            raise ImportError("You need to install the 'local' extra requirements to use local embeddings models")

        super().__init__(model_name, default_options)
        self.api_key = api_key

    @cached_property
    def client(self) -> PreTrainedModel:
        """
        Client for the LLM.

        Returns:
            The client used to interact with the LLM.
        """
        return LocalEmbeddingsClient(model_name=self.model_name, hf_api_key=self.api_key)
