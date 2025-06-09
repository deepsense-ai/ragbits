import asyncio
import base64

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.litellm import LiteLLMEmbedderOptions

try:
    import litellm
    from litellm.llms.vertex_ai.common_utils import VertexAIError
    from litellm.main import VertexMultimodalEmbedding

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.dense.base import DenseEmbedder
from ragbits.core.embeddings.exceptions import (
    EmbeddingResponseError,
    EmbeddingStatusError,
)


class VertexAIMultimodelEmbedder(DenseEmbedder[LiteLLMEmbedderOptions]):
    """
    Client for creating text embeddings using LiteLLM API.
    """

    options_cls = LiteLLMEmbedderOptions
    VERTEX_AI_PREFIX = "vertex_ai/"

    def __init__(
        self,
        model_name: str = "multimodalembedding",
        api_base: str | None = None,
        base_url: str | None = None,  # Alias for api_base
        api_key: str | None = None,
        concurency: int = 10,
        default_options: LiteLLMEmbedderOptions | None = None,
    ) -> None:
        """
        Constructs the embedding client for multimodal VertexAI models.

        Args:
            model_name: One of the VertexAI multimodal models to be used. Default is "multimodalembedding".
            api_base: The API endpoint you want to call the model with.
            base_url: Alias for api_base. If both are provided, api_base takes precedence.
            api_key: API key to be used. If not specified, an environment variable will be used.
            concurency: The number of concurrent requests to make to the API.
            default_options: Additional options to pass to the API.

        Raises:
            ImportError: If the 'litellm' extra requirements are not installed.
            ValueError: If the chosen model is not supported by VertexAI multimodal embeddings.
        """
        if not HAS_LITELLM:
            raise ImportError("You need to install the 'litellm' extra requirements to use LiteLLM embeddings models")

        super().__init__(default_options=default_options)

        if model_name.startswith(self.VERTEX_AI_PREFIX):
            model_name = model_name[len(self.VERTEX_AI_PREFIX) :]

        self.model_name = model_name
        self.api_base = api_base or base_url
        self.api_key = api_key
        self.concurency = concurency

        supported_models = VertexMultimodalEmbedding().SUPPORTED_MULTIMODAL_EMBEDDING_MODELS
        if model_name not in supported_models:
            raise ValueError(f"Model {model_name} is not supported by VertexAI multimodal embeddings")

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this VertexAI multimodal model.

        Embeds a sample text to determine the dimension.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        sample_embedding = await self.embed_text(["sample"])
        return VectorSize(size=len(sample_embedding[0]), is_sparse=False)

    async def _embed(self, data: list[dict], options: LiteLLMEmbedderOptions | None = None) -> list[dict]:
        """
        Creates embeddings for the given data. The format is defined in the VertexAI API:
        https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings

        Args:
            data: List of instances in the format expected by the VertexAI API.
            options: Additional options to pass to the VertexAI multimodal embeddings API.

        Returns:
            List of embeddings for the given VertexAI instances, each instance is a dictionary
            in the format returned by the VertexAI API.

        Raises:
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            data=data,
            model=self.model_name,
            api_base=self.api_base,
            options=merged_options.dict(),
        ) as outputs:
            semaphore = asyncio.Semaphore(self.concurency)
            try:
                response = await asyncio.gather(
                    *[self._call_litellm(instance, semaphore, merged_options) for instance in data],
                )
            except VertexAIError as exc:
                raise EmbeddingStatusError(exc.message, exc.status_code) from exc

            outputs.embeddings = []
            for i, embedding in enumerate(response):
                if embedding.data is None or not embedding.data:
                    raise EmbeddingResponseError(f"No embeddings returned for instance {i}")
                outputs.embeddings.append(embedding.data[0])

            return outputs.embeddings

    async def _call_litellm(
        self, instance: dict, semaphore: asyncio.Semaphore, options: LiteLLMEmbedderOptions
    ) -> litellm.EmbeddingResponse:
        """
        Calls the LiteLLM API to get embeddings for the given data.

        Args:
            instance: Single VertexAI instance to get embeddings for.
            semaphore: Semaphore to limit the number of concurrent requests.
            options: Additional options to pass to the VertexAI multimodal embeddings API.

        Returns:
            List of embeddings for the given LiteLLM instances.
        """
        async with semaphore:
            response = await litellm.aembedding(
                input=[instance],
                model=f"{self.VERTEX_AI_PREFIX}{self.model_name}",
                api_base=self.api_base,
                api_key=self.api_key,
                **options.dict(),
            )

        return response

    async def embed_text(self, data: list[str], options: LiteLLMEmbedderOptions | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the VertexAI multimodal embeddings API.

        Returns:
            List of embeddings for the given strings.

        Raises:
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """
        response = await self._embed([{"text": text} for text in data], options=options)
        return [embedding["embedding"] for embedding in response]

    def image_support(self) -> bool:  # noqa: PLR6301
        """
        Check if the model supports image embeddings.

        Returns:
            True if the model supports image embeddings, False otherwise.
        """
        return True

    async def embed_image(
        self, images: list[bytes], options: LiteLLMEmbedderOptions | None = None
    ) -> list[list[float]]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.
            options: Additional options to pass to the VertexAI multimodal embeddings API.

        Returns:
            List of embeddings for the given images.

        Raises:
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
        """
        images_b64 = (base64.b64encode(image).decode() for image in images)
        response = await self._embed(
            [{"image": {"bytesBase64Encoded": image}} for image in images_b64], options=options
        )
        return [embedding["embedding"] for embedding in response]
