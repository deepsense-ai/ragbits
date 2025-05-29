from typing import Any, cast

import litellm
from typing_extensions import Self

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.base import DenseEmbedder
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingEmptyResponseError,
    EmbeddingResponseError,
    EmbeddingStatusError,
)
from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven


class LiteLLMEmbedderOptions(Options):
    """
    Dataclass that represents available call options for the LiteLLMEmbeddingClient client.
    Each of them is described in the [LiteLLM documentation](https://docs.litellm.ai/docs/embedding/supported_embedding#optional-litellm-fields).
    """

    dimensions: int | None | NotGiven = NOT_GIVEN
    timeout: int | None | NotGiven = NOT_GIVEN
    user: str | None | NotGiven = NOT_GIVEN
    encoding_format: str | None | NotGiven = NOT_GIVEN


class LiteLLMEmbedder(DenseEmbedder[LiteLLMEmbedderOptions]):
    """
    Client for creating text embeddings using LiteLLM API.
    """

    options_cls = LiteLLMEmbedderOptions

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        default_options: LiteLLMEmbedderOptions | None = None,
        *,
        api_base: str | None = None,
        base_url: str | None = None,  # Alias for api_base
        api_key: str | None = None,
        api_version: str | None = None,
        router: litellm.Router | None = None,
    ) -> None:
        """
        Constructs the LiteLLMEmbeddingClient.

        Args:
            model_name: Name of the [LiteLLM supported model](https://docs.litellm.ai/docs/embedding/supported_embedding)\
                to be used. Default is "text-embedding-3-small".
            default_options: Default options to pass to the LiteLLM API.
            api_base: The API endpoint you want to call the model with.
            base_url: Alias for api_base. If both are provided, api_base takes precedence.
            api_key: API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/embedding/supported_embedding).
            api_version: The API version for the call.
            router: Router to be used to [route requests](https://docs.litellm.ai/docs/routing) to different models.
        """
        super().__init__(default_options=default_options)

        self.model_name = model_name
        self.api_base = api_base or base_url
        self.api_key = api_key
        self.api_version = api_version
        self.router = router

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this LiteLLM model.

        If dimensions are specified in default options, use that value.
        Otherwise, embed a sample text to determine the dimension.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        # Check if dimensions are explicitly set in default options
        if (
            self.default_options
            and self.default_options.dimensions is not NOT_GIVEN
            and self.default_options.dimensions is not None
        ):
            # We've checked that dimensions is not None and not NOT_GIVEN, so it must be int
            return VectorSize(size=cast(int, self.default_options.dimensions), is_sparse=False)

        # If no dimensions specified, embed a sample text to determine size
        sample_embedding = await self.embed_text(["sample"])
        return VectorSize(size=len(sample_embedding[0]), is_sparse=False)

    async def embed_text(self, data: list[str], options: LiteLLMEmbedderOptions | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the Lite LLM API.

        Returns:
            List of embeddings for the given strings.

        Raises:
            EmbeddingConnectionError: If there is a connection error with the embedding API.
            EmbeddingEmptyResponseError: If the embedding API returns an empty response.
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        with trace(
            data=data,
            model=self.model_name,
            api_base=self.api_base,
            api_version=self.api_version,
            options=merged_options.dict(),
        ) as outputs:
            try:
                entrypoint = self.router or litellm
                response = await entrypoint.aembedding(
                    input=data,
                    model=self.model_name,
                    api_base=self.api_base,
                    api_key=self.api_key,
                    api_version=self.api_version,
                    **merged_options.dict(),
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

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Self:
        """
        Creates and returns a LiteLLMEmbedder instance.

        Args:
            config: A configuration object containing the configuration for initializing the LiteLLMEmbedder instance.

        Returns:
            LiteLLMEmbedder: An initialized LiteLLMEmbedder instance.
        """
        if "router" in config:
            router = litellm.router.Router(model_list=config["router"])
            config["router"] = router

        # Map base_url to api_base if present
        if "base_url" in config and "api_base" not in config:
            config["api_base"] = config.pop("base_url")

        return super().from_config(config)
