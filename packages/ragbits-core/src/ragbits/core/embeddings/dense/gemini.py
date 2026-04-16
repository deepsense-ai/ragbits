from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.base import DenseEmbedder
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingEmptyResponseError,
    EmbeddingStatusError,
)
from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven

try:
    from google import genai
    from google.api_core import exceptions as google_exceptions
    from google.genai import types as genai_types

    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    genai = None  # type: ignore[assignment]
    google_exceptions = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from google.genai import types as genai_types
    from PIL.Image import Image as PILImage


class GeminiEmbedderOptions(Options):
    """
    Dataclass that represents available call options for the GeminiEmbedder client.
    Each of them is described in the
    [Google Gemini API documentation](https://ai.google.dev/gemini-api/docs/embeddings).
    """

    output_dimensionality: int | None | NotGiven = NOT_GIVEN
    task_type: str | None | NotGiven = NOT_GIVEN


class GeminiEmbedder(DenseEmbedder[GeminiEmbedderOptions]):
    """
    Client for creating text embeddings using the Google Gemini API directly.
    """

    options_cls = GeminiEmbedderOptions

    def __init__(
        self,
        model_name: str = "text-embedding-004",
        default_options: GeminiEmbedderOptions | None = None,
        *,
        api_key: str | None = None,
    ) -> None:
        """
        Constructs the GeminiEmbedder.

        Args:
            model_name: Name of the Gemini embedding model to use. Default is "text-embedding-004".
            default_options: Default options to pass to the Gemini API.
            api_key: Google API key. If not specified, the GOOGLE_API_KEY environment variable will be used.
        """
        if not HAS_GEMINI:
            raise ImportError(
                "You need to install the 'google-genai' package to use GeminiEmbedder."
                " Please install ragbits-core with the 'gemini' extra: pip install ragbits-core[gemini]"
            )
        super().__init__(default_options=default_options)
        self.model_name = model_name
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    async def get_vector_size(self) -> VectorSize:
        """
        Get the vector size for this Gemini model.

        If output_dimensionality is specified in default options, use that value.
        Otherwise, embed a sample text to determine the dimension.

        Returns:
            VectorSize object with the model's embedding dimension.
        """
        if (
            self.default_options
            and self.default_options.output_dimensionality is not NOT_GIVEN
            and self.default_options.output_dimensionality is not None
        ):
            return VectorSize(size=cast(int, self.default_options.output_dimensionality), is_sparse=False)

        sample_embedding = await self.embed_text(["sample"])
        return VectorSize(size=len(sample_embedding[0]), is_sparse=False)

    async def embed_text(self, data: list[str], options: GeminiEmbedderOptions | None = None) -> list[list[float]]:
        """
        Creates embeddings for the given strings.

        Args:
            data: List of strings to get embeddings for.
            options: Additional options to pass to the Gemini API.

        Returns:
            List of embeddings for the given strings.

        Raises:
            EmbeddingConnectionError: If there is a connection error with the embedding API.
            EmbeddingEmptyResponseError: If the embedding API returns an empty response.
            EmbeddingStatusError: If the embedding API returns an error status code.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        options_dict = merged_options.dict()

        config: genai_types.EmbedContentConfig | None = None
        if "output_dimensionality" in options_dict:
            config = genai_types.EmbedContentConfig(output_dimensionality=options_dict["output_dimensionality"])
        if "task_type" in options_dict:
            config = (
                genai_types.EmbedContentConfig(task_type=options_dict["task_type"])
                if config is None
                else genai_types.EmbedContentConfig(
                    output_dimensionality=config.output_dimensionality, task_type=options_dict["task_type"]
                )
            )

        with trace(
            data=data,
            model=self.model_name,
            options=options_dict,
        ) as outputs:
            try:
                contents: list[str | PILImage | genai_types.File | genai_types.Part] = cast(
                    "list[str | PILImage | genai_types.File | genai_types.Part]", data
                )
                response = await self.client.aio.models.embed_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            except google_exceptions.GoogleAPICallError as exc:
                status_code = exc.code if exc.code is not None else 500
                raise EmbeddingStatusError(str(exc), status_code) from exc
            except google_exceptions.GoogleAPIError as exc:
                raise EmbeddingConnectionError(str(exc)) from exc

            if not response.embeddings:
                raise EmbeddingEmptyResponseError()

            outputs.embeddings = [embedding.values for embedding in response.embeddings]

        return outputs.embeddings
