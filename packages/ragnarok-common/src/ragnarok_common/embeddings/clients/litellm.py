from dataclasses import dataclass
from typing import Optional, Union

try:
    import litellm

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

from ...types import NOT_GIVEN, NotGiven
from .base import EmbeddingsClient, EmbeddingsOptions
from .exceptions import EmbeddingConnectionError, EmbeddingResponseError, EmbeddingStatusError


@dataclass
class LiteLLMOptions(EmbeddingsOptions):
    """
    Dataclass that represents all available encoder call options for the LiteLLM client.
    """

    dimensions: Union[Optional[int], NotGiven] = NOT_GIVEN
    encoding_format: Union[Optional[str], NotGiven] = NOT_GIVEN


class LiteLLMEmbeddingsClient(EmbeddingsClient):
    """
    Client for the LiteLLM that supports calls to various encoders' APIs, including OpenAI, VertexAI,
    Hugging Face and others.
    """

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        """
        Constructs the LiteLLMEmbeddingClient.

        Args:
            model_name: Name of the [LiteLLM supported model]
            (https://docs.litellm.ai/docs/embedding/supported_embedding)\
            to be used. Default is "text-embedding-3-small".
            api_base: The API endpoint you want to call the model with.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/embedding/supported_embedding).
            api_version: The API version for the call.

        Raises:
            ImportError: If the litellm package is not installed.
        """
        if not HAS_LITELLM:
            raise ImportError("You need to install litellm package to use LiteLLM models")

        super().__init__(model_name)
        self.api_base = api_base
        self.api_key = api_key
        self.api_version = api_version

    async def call(self, data: list[str], options: LiteLLMOptions) -> list[list[float]]:
        """
        Calls the appropriate encoder endpoint with the given data and options.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the LiteLLM API.

        Returns:
            List of embeddings for the given strings.

        Raises:
            EmbeddingConnectionError: If there is a connection error with the embedding API.
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """

        try:
            response = await litellm.aembedding(
                input=data,
                model=self.model_name,
                api_base=self.api_base,
                api_key=self.api_key,
                api_version=self.api_version,
                **options,
            )
        except litellm.openai.APIConnectionError as exc:
            raise EmbeddingConnectionError() from exc
        except litellm.openai.APIStatusError as exc:
            raise EmbeddingStatusError(exc.message, exc.status_code) from exc
        except litellm.openai.APIResponseValidationError as exc:
            raise EmbeddingResponseError() from exc

        return [embedding["embedding"] for embedding in response.data]
