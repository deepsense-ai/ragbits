import asyncio
import base64

import litellm
from litellm.main import VertexMultimodalEmbedding
from litellm.types.llms.vertex_ai import Instance, InstanceImage

from ragbits.core.audit import trace
from ragbits.core.embeddings import Embedder
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


class LiteLLMEmbedder(Embedder[LiteLLMEmbedderOptions]):
    """
    Client for creating text embeddings using LiteLLM API.
    """

    options_cls = LiteLLMEmbedderOptions

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        default_options: LiteLLMEmbedderOptions | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
    ) -> None:
        """
        Constructs the LiteLLMEmbeddingClient.

        Args:
            model: Name of the [LiteLLM supported model](https://docs.litellm.ai/docs/embedding/supported_embedding)\
                to be used. Default is "text-embedding-3-small".
            default_options: Default options to pass to the LiteLLM API.
            api_base: The API endpoint you want to call the model with.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/embedding/supported_embedding).
            api_version: The API version for the call.
        """
        super().__init__(default_options=default_options)
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.api_version = api_version

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
            model=self.model,
            api_base=self.api_base,
            api_version=self.api_version,
            options=merged_options.dict(),
        ) as outputs:
            try:
                response = await litellm.aembedding(
                    input=data,
                    model=self.model,
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

    def image_support(self) -> bool:  # noqa: PLR6301
        """
        Check if the model supports image embeddings.

        Returns:
            True if the model supports image embeddings, False otherwise.
        """
        # If not in our dictionary, we'll try a more dynamic approach
        model_name = self.model.replace("vertexai/", "").lower()

        # Check against known supported models
        supported_models = VertexMultimodalEmbedding().SUPPORTED_MULTIMODAL_EMBEDDING_MODELS

        return model_name in supported_models

    async def process_image(self, image_instance: Instance, options: Options) -> list[float]:
        """
        Embeds a single image from the given instance.

        Args:
            image_instance: Instance of the image to embed.
            options: Additional options to pass to the Lite LLM API.

        Returns:
            list of floats representing the embedded image.
        """
        response = await litellm.aembedding(
            model=self.model,
            input=image_instance,
            api_base=self.api_base,
            api_key=self.api_key,
            api_version=self.api_version,
            **options.dict(),
        )
        return response.data[0].embedding

    async def embed_image(self, images: list[bytes], options: Options | None = None) -> list[list[float]]:
        """
        Embeds a list of images into a list of vectors.

        Args:
            images: A list of input image bytes to embed.
            options: Additional settings used by the Embedder model.

        Returns:
            A list of embedding vectors, one for each input image.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            model=self.model,
            api_base=self.api_base,
            api_version=self.api_version,
            options=merged_options.dict(),
        ) as outputs:
            base64_images = [base64.b64encode(img).decode("utf-8") for img in images]
            instances = [Instance(image=InstanceImage(bytesBase64Encoded=base64_img)) for base64_img in base64_images]
            try:
                embeddings = await asyncio.gather(
                    *[self.process_image(instance, merged_options) for instance in instances]
                )

            except litellm.openai.APIConnectionError as exc:
                raise EmbeddingConnectionError() from exc
            except litellm.openai.APIStatusError as exc:
                raise EmbeddingStatusError(exc.message, exc.status_code) from exc
            except litellm.openai.APIResponseValidationError as exc:
                raise EmbeddingResponseError() from exc

            outputs.embeddings = embeddings
            return embeddings
