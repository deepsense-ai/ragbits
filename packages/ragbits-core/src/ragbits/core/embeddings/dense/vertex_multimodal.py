from __future__ import annotations

import asyncio
import base64
import binascii
import logging
from typing import cast

import filetype

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven

try:
    from google import genai
    from google.api_core import exceptions as google_exceptions
    from google.genai import types as genai_types

    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False
    genai = None  # type: ignore[assignment]
    google_exceptions = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

try:
    import google.auth
    import google.auth.transport.requests

    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

import aiohttp

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.dense.base import DenseEmbedder
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingResponseError,
    EmbeddingStatusError,
)

logger = logging.getLogger(__name__)
HTTP_STATUS_OK = 200


class VertexAIMultimodalEmbedderOptions(Options):
    """
    Dataclass that represents available call options for the VertexAIMultimodalEmbedder client.
    """

    dimensions: int | None | NotGiven = NOT_GIVEN
    timeout: int | None | NotGiven = NOT_GIVEN


class VertexAIMultimodalEmbedder(DenseEmbedder[VertexAIMultimodalEmbedderOptions]):
    """
    Client for creating multimodal embeddings using Google Vertex AI.

    Supports two model families:
    - Modern models (gemini-embedding-*): Uses the google-genai SDK directly.
    - Legacy models (multimodalembedding*): Uses direct HTTP calls to the Vertex AI predict endpoint.
    """

    options_cls = VertexAIMultimodalEmbedderOptions

    def __init__(
        self,
        model_name: str = "multimodalembedding",
        api_base: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        project: str | None = None,
        location: str | None = None,
        concurrency: int = 10,
        default_options: VertexAIMultimodalEmbedderOptions | None = None,
    ) -> None:
        """
        Constructs the embedding client for multimodal Vertex AI models.

        Args:
            model_name: Name of the embedding model to use. Default is "multimodalembedding".
            api_base: The API endpoint you want to call the model with.
            base_url: Alias for api_base. If both are provided, api_base takes precedence.
            api_key: API key for modern gemini-embedding-* models. Legacy models use Application Default Credentials.
            project: Google Cloud project ID. If not specified, inferred from environment.
            location: Google Cloud region. If not specified, defaults to "us-central1".
            concurrency: The number of concurrent requests to make to the API.
            default_options: Additional options to pass to the API.

        Raises:
            ImportError: If required packages are not installed.
        """
        if self._is_legacy_model_name(model_name):
            if not HAS_GOOGLE_AUTH:
                raise ImportError(
                    "You need to install the 'google-auth' package to use VertexAIMultimodalEmbedder"
                    " with legacy models. Please install ragbits-core with the 'vertex' extra:"
                    " pip install ragbits-core[vertex]"
                )
        elif not HAS_GOOGLE_GENAI:
            raise ImportError(
                "You need to install the 'google-genai' package to use VertexAIMultimodalEmbedder."
                " Please install ragbits-core with the 'vertex' extra:"
                " pip install ragbits-core[vertex]"
            )

        super().__init__(default_options=default_options)

        self.model_name = model_name
        self.api_base = api_base or base_url
        self.api_key = api_key
        self.project = project
        self.location = location or "us-central1"
        self.concurrency = concurrency
        if self.concurrency < 1:
            raise ValueError("concurrency must be >= 1")

        if not self._is_legacy_model:
            http_options = genai_types.HttpOptions(base_url=self.api_base) if self.api_base else None
            self._client = genai.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
                api_key=self.api_key,
                http_options=http_options,
            )

    @staticmethod
    def _is_legacy_model_name(model_name: str) -> bool:
        """
        Check if a model name refers to a legacy multimodalembedding model.

        Args:
            model_name: The model name to check.

        Returns:
            True if the model is a legacy model, False otherwise.
        """
        return not model_name.startswith("gemini-embedding")

    @property
    def _is_legacy_model(self) -> bool:
        """Check if the current model is a legacy multimodalembedding model."""
        return self._is_legacy_model_name(self.model_name)

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this Vertex AI multimodal model.

        Embeds a sample text to determine the dimension.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        sample_embedding = await self.embed_text(["sample"])
        return VectorSize(size=len(sample_embedding[0]), is_sparse=False)

    async def _embed(self, data: list[dict], options: VertexAIMultimodalEmbedderOptions | None = None) -> list[dict]:
        """
        Creates embeddings for the given data.

        Args:
            data: List of instances. Each instance is a dict with either a "text" key
                or an "image" key containing {"bytesBase64Encoded": "..."}.
            options: Additional options to pass to the embedding API.

        Returns:
            List of dicts, each with an "embedding" key containing the embedding vector.

        Raises:
            EmbeddingStatusError: If the embedding API returns an error status code.
            EmbeddingResponseError: If the embedding API response is invalid.
            EmbeddingConnectionError: If there is a connection error with the embedding API.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            data=data,
            model=self.model_name,
            api_base=self.api_base,
            options=merged_options.dict(),
        ) as outputs:
            semaphore = asyncio.Semaphore(self.concurrency)
            timeout = merged_options.dict().get("timeout")
            if timeout is not None and timeout <= 0:
                raise ValueError("timeout must be > 0 or None")

            if self._is_legacy_model:
                response = await self._embed_legacy(data, semaphore, merged_options, timeout)
            else:
                response = await self._embed_modern(data, semaphore, merged_options, timeout)

            outputs.embeddings = response
            return outputs.embeddings

    async def _embed_modern(
        self,
        data: list[dict],
        semaphore: asyncio.Semaphore,
        options: VertexAIMultimodalEmbedderOptions,
        timeout: int | None = None,
    ) -> list[dict]:
        """
        Embed using the google-genai SDK for modern gemini-embedding models.

        Args:
            data: List of instance dicts with "text" or "image" keys.
            semaphore: Semaphore to limit concurrent requests.
            options: Embedding options.
            timeout: Timeout for each request in seconds. If None, provider defaults are used.

        Returns:
            List of dicts with "embedding" key.

        Raises:
            EmbeddingStatusError: If the API returns an error status code.
            EmbeddingConnectionError: If there is a connection error.
            EmbeddingResponseError: If the response is invalid.
        """
        config: genai_types.EmbedContentConfig | None = None
        options_dict = options.dict()
        if options_dict.get("dimensions") is not None:
            config = genai_types.EmbedContentConfig(output_dimensionality=options_dict["dimensions"])

        async def call(instance: dict) -> dict:
            try:
                content = self._instance_to_content(instance)
            except (TypeError, KeyError, ValueError) as exc:
                raise EmbeddingResponseError(str(exc)) from exc

            async with semaphore:
                try:
                    call_coro = self._client.aio.models.embed_content(
                        model=self.model_name,
                        contents=content,
                        config=config,
                    )
                    if timeout is not None:
                        response = await asyncio.wait_for(call_coro, timeout=timeout)
                    else:
                        response = await call_coro
                except TimeoutError as exc:
                    raise EmbeddingConnectionError("Request timed out.") from exc
                except google_exceptions.GoogleAPICallError as exc:
                    status_code = exc.code if exc.code is not None else 500
                    raise EmbeddingStatusError(str(exc), status_code) from exc
                except google_exceptions.GoogleAPIError as exc:
                    raise EmbeddingConnectionError(str(exc)) from exc

            if not response.embeddings:
                raise EmbeddingResponseError("No embeddings returned")
            values = response.embeddings[0].values
            if values is None:
                raise EmbeddingResponseError("No embedding values returned")
            return {"embedding": cast(list[float], list(values))}

        results = await asyncio.gather(*[call(instance) for instance in data])
        return list(results)

    @staticmethod
    def _instance_to_content(instance: dict) -> genai_types.Content:
        """
        Convert an instance dict to a genai Content object.

        Args:
            instance: Dict with "text" or "image" key.

        Returns:
            A genai Content object suitable for embed_content.
        """
        if "text" in instance:
            text = instance["text"]
            if not isinstance(text, str):
                raise ValueError("Text instance must contain a string under 'text'.")
            return genai_types.Content(parts=[genai_types.Part(text=text)])

        if "image" in instance:
            image_data = instance["image"]
            if not isinstance(image_data, dict) or "bytesBase64Encoded" not in image_data:
                raise ValueError("Image instance must contain {'bytesBase64Encoded': <base64-string>} payload.")
            image_b64 = image_data["bytesBase64Encoded"]
            if not isinstance(image_b64, str):
                raise ValueError("Image payload 'bytesBase64Encoded' must be a base64 string.")
            try:
                image_bytes = base64.b64decode(image_b64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError("Invalid base64-encoded image payload.") from exc
            mime_type = filetype.guess_mime(image_bytes) or "image/jpeg"
            return genai_types.Content(parts=[genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)])

        raise ValueError(f"Instance must have 'text' or 'image' key, got: {list(instance.keys())}")

    async def _embed_legacy(
        self,
        data: list[dict],
        semaphore: asyncio.Semaphore,
        options: VertexAIMultimodalEmbedderOptions,
        timeout: int | None = None,
    ) -> list[dict]:
        """
        Embed using direct HTTP calls for legacy multimodalembedding models.

        Args:
            data: List of instance dicts with "text" or "image" keys.
            semaphore: Semaphore to limit concurrent requests.
            options: Embedding options.
            timeout: Timeout for each request in seconds. If None, provider defaults are used.

        Returns:
            List of dicts with "embedding" key.

        Raises:
            EmbeddingStatusError: If the API returns an error status code.
            EmbeddingConnectionError: If there is a connection error.
            EmbeddingResponseError: If the response is invalid.
        """
        try:
            credentials, project = google.auth.default()
            project = self.project or project
            if not project:
                raise EmbeddingConnectionError(
                    "Google Cloud project could not be determined. Set the 'project' parameter."
                )

            if not credentials.valid:
                request = google.auth.transport.requests.Request()
                await asyncio.to_thread(credentials.refresh, request)
            token = credentials.token
        except EmbeddingConnectionError:
            raise
        except Exception as exc:
            raise EmbeddingConnectionError(f"Failed to authenticate with Google Cloud: {exc}") from exc

        if self.api_base:
            url = (
                f"{self.api_base.rstrip('/')}/v1/projects/{project}/locations/"
                f"{self.location}/publishers/google/models/{self.model_name}:predict"
            )
        else:
            url = (
                f"https://{self.location}-aiplatform.googleapis.com/v1/"
                f"projects/{project}/locations/{self.location}/"
                f"publishers/google/models/{self.model_name}:predict"
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        client_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None

        async def call(session: aiohttp.ClientSession, instance: dict) -> dict:
            async with semaphore:
                try:
                    async with session.post(
                        url,
                        headers=headers,
                        json={"instances": [instance]},
                        timeout=client_timeout,
                    ) as resp:
                        if resp.status != HTTP_STATUS_OK:
                            body = await resp.text()
                            raise EmbeddingStatusError(body, resp.status)
                        result = await resp.json()
                except aiohttp.ClientError as exc:
                    raise EmbeddingConnectionError(str(exc)) from exc

            predictions = result.get("predictions")
            if not predictions:
                raise EmbeddingResponseError("No predictions returned from Vertex AI")

            prediction = predictions[0]
            if "textEmbedding" in prediction:
                return {"embedding": prediction["textEmbedding"]}
            if "imageEmbedding" in prediction:
                return {"embedding": prediction["imageEmbedding"]}

            raise EmbeddingResponseError(f"Unexpected prediction format: {list(prediction.keys())}")

        async with aiohttp.ClientSession() as client_session:
            results = await asyncio.gather(*[call(client_session, instance) for instance in data])
        return list(results)

    async def embed_text(
        self, data: list[str], options: VertexAIMultimodalEmbedderOptions | None = None
    ) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the embedding API.

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
        self, images: list[bytes], options: VertexAIMultimodalEmbedderOptions | None = None
    ) -> list[list[float]]:
        """
        Creates embeddings for the given images.

        Args:
            images: List of images to get embeddings for.
            options: Additional options to pass to the embedding API.

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


# Backwards compatibility alias for the old typo in class name.
VertexAIMultimodelEmbedder = VertexAIMultimodalEmbedder
