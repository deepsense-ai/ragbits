from typing import cast

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

try:
    import openai
    from openai import AsyncOpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIEmbedderOptions(Options):
    """
    Dataclass that represents available call options for the OpenAIEmbedder client.
    Each of them is described in the
    [OpenAI API documentation](https://platform.openai.com/docs/api-reference/embeddings/create).
    """

    dimensions: int | None | NotGiven = NOT_GIVEN
    timeout: int | None | NotGiven = NOT_GIVEN
    user: str | None | NotGiven = NOT_GIVEN
    encoding_format: str | None | NotGiven = NOT_GIVEN


class OpenAIEmbedder(DenseEmbedder[OpenAIEmbedderOptions]):
    """
    Client for creating text embeddings using the OpenAI API directly.
    """

    options_cls = OpenAIEmbedderOptions

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        default_options: OpenAIEmbedderOptions | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """
        Constructs the OpenAIEmbedder.

        Args:
            model_name: Name of the OpenAI embedding model to use. Default is "text-embedding-3-small".
            default_options: Default options to pass to the OpenAI API.
            api_key: OpenAI API key. If not specified, the OPENAI_API_KEY environment variable will be used.
            base_url: Custom API base URL (e.g. for Azure OpenAI or compatible APIs).
        """
        if not HAS_OPENAI:
            raise ImportError(
                "You need to install the 'openai' package to use OpenAIEmbedder."
                " Please install ragbits-core with the 'openai' extra: pip install ragbits-core[openai]"
            )
        super().__init__(default_options=default_options)
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this OpenAI model.

        If dimensions are specified in default options, use that value.
        Otherwise, embed a sample text to determine the dimension.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        if (
            self.default_options
            and self.default_options.dimensions is not NOT_GIVEN
            and self.default_options.dimensions is not None
        ):
            return VectorSize(size=cast(int, self.default_options.dimensions), is_sparse=False)

        sample_embedding = await self.embed_text(["sample"])
        return VectorSize(size=len(sample_embedding[0]), is_sparse=False)

    async def embed_text(self, data: list[str], options: OpenAIEmbedderOptions | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the OpenAI API.

        Returns:
            List of embeddings for the given strings.

        Raises:
            EmbeddingConnectionError: If there is a connection error with the embedding API.
            EmbeddingEmptyResponseError: If the embedding API returns an empty response.
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        options_dict = merged_options.dict()
        timeout = options_dict.pop("timeout", None)

        with trace(
            data=data,
            model=self.model_name,
            base_url=self.base_url,
            options=options_dict,
        ) as outputs:
            try:
                response = await self.client.embeddings.create(
                    input=data,
                    model=self.model_name,
                    timeout=timeout,
                    **options_dict,
                )
            except openai.APIConnectionError as exc:
                raise EmbeddingConnectionError() from exc
            except openai.APIStatusError as exc:
                raise EmbeddingStatusError(exc.message, exc.status_code) from exc
            except openai.APIResponseValidationError as exc:
                raise EmbeddingResponseError() from exc

            if not response.data:
                raise EmbeddingEmptyResponseError()

            outputs.embeddings = [embedding.embedding for embedding in response.data]
            if response.usage:
                outputs.prompt_tokens = response.usage.prompt_tokens
                outputs.total_tokens = response.usage.total_tokens

        return outputs.embeddings

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self.client.aclose()
