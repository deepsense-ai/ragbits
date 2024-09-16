from functools import cached_property
from typing import Optional

from .base import Embeddings
from .clients.litellm import LiteLLMEmbeddingsClient, LiteLLMOptions


from ragbits_common.embeddings.base import Embeddings
from ragbits_common.embeddings.exceptions import EmbeddingConnectionError, EmbeddingResponseError, EmbeddingStatusError


class LiteLLMEmbeddings(Embeddings):
    """
    Class for interaction with any encoder supported by LiteLLM API.
    """

    _options_cls = LiteLLMOptions

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        default_options: Optional[LiteLLMOptions] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        """
        Constructs a new LiteLLMEmbeddings instance.

        Args:
            model_name: Name of the
                [LiteLLM supported model](https://docs.litellm.ai/docs/embedding/supported_embedding)
                to be used. Default is "text-embedding-3-small".
            default_options: Default options to be used.
            api_base: The API endpoint you want to call the model with.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/embedding/supported_embedding).
            api_version: The API version for the call.

        """

        super().__init__(model_name, default_options)
        self.api_base = api_base
        self.api_key = api_key
        self.api_version = api_version

    @cached_property
    def client(self) -> LiteLLMEmbeddingsClient:
        """
        Client for the LiteLLM encoder.
        """
        return LiteLLMEmbeddingsClient(
            model_name=self.model_name,
            api_base=self.api_base,
            api_key=self.api_key,
            api_version=self.api_version,
        )
