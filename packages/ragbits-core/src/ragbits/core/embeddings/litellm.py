try:
    import litellm

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

from ragbits.core.audit import trace
from ragbits.core.embeddings import Embeddings
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingEmptyResponseError,
    EmbeddingResponseError,
    EmbeddingStatusError,
)


class LiteLLMEmbeddings(Embeddings):
    """
    Client for creating text embeddings using LiteLLM API.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        options: dict | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
    ) -> None:
        """
        Constructs the LiteLLMEmbeddingClient.

        Args:
            model: Name of the [LiteLLM supported model](https://docs.litellm.ai/docs/embedding/supported_embedding)\
                to be used. Default is "text-embedding-3-small".
            options: Additional options to pass to the LiteLLM API.
            api_base: The API endpoint you want to call the model with.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/embedding/supported_embedding).
            api_version: The API version for the call.

        Raises:
            ImportError: If the 'litellm' extra requirements are not installed.
        """
        if not HAS_LITELLM:
            raise ImportError("You need to install the 'litellm' extra requirements to use LiteLLM embeddings models")

        super().__init__()
        self.model = model
        self.options = options or {}
        self.api_base = api_base
        self.api_key = api_key
        self.api_version = api_version

    async def embed_text(self, data: list[str]) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.

        Returns:
            List of embeddings for the given strings.

        Raises:
            EmbeddingConnectionError: If there is a connection error with the embedding API.
            EmbeddingEmptyResponseError: If the embedding API returns an empty response.
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """
        with trace(
            data=data,
            model=self.model,
            api_base=self.api_base,
            api_version=self.api_version,
            options=self.options,
        ) as outputs:
            try:
                response = await litellm.aembedding(
                    input=data,
                    model=self.model,
                    api_base=self.api_base,
                    api_key=self.api_key,
                    api_version=self.api_version,
                    **self.options,
                )
            except litellm.openai.APIConnectionError as exc:
                raise EmbeddingConnectionError() from exc
            except litellm.openai.APIStatusError as exc:
                raise EmbeddingStatusError(exc.message, exc.status_code) from exc
            except litellm.openai.APIResponseValidationError as exc:
                raise EmbeddingResponseError() from exc

            if not response.data:
                raise EmbeddingEmptyResponseError()

            outputs.embeddings = [embedding["embedding"] for embedding in response.data]
            if response.usage:
                outputs.completion_tokens = response.usage.completion_tokens
                outputs.prompt_tokens = response.usage.prompt_tokens
                outputs.total_tokens = response.usage.total_tokens

        return outputs.embeddings
