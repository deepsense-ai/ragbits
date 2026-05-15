from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.gemini import GeminiEmbedder, GeminiEmbedderOptions
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingEmptyResponseError,
    EmbeddingStatusError,
)
from ragbits.core.types import NOT_GIVEN


@pytest.fixture(autouse=True)
def mock_genai_types():
    from types import SimpleNamespace

    mock_types = MagicMock()
    mock_types.EmbedContentConfig.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    with patch("ragbits.core.embeddings.dense.gemini.genai_types", mock_types):
        yield mock_types


def create_mock_response(embeddings_data: list[list[float]]) -> MagicMock:
    """Create a mock response object that mimics the Gemini response structure."""
    mock_response = MagicMock()
    mock_embeddings = []
    for values in embeddings_data:
        mock_embedding = MagicMock()
        mock_embedding.values = values
        mock_embeddings.append(mock_embedding)
    mock_response.embeddings = mock_embeddings
    return mock_response


def _make_embedder(
    model_name: str = "text-embedding-004",
    default_options: GeminiEmbedderOptions | None = None,
) -> GeminiEmbedder:
    """Create a GeminiEmbedder with a stub client (no real google-genai SDK needed)."""
    mock_client = MagicMock()
    with (
        patch("ragbits.core.embeddings.dense.gemini.HAS_GEMINI", True),
        patch("ragbits.core.embeddings.dense.gemini.genai", create=True) as mock_genai,
    ):
        mock_genai.Client.return_value = mock_client
        embedder = GeminiEmbedder(model_name=model_name, default_options=default_options)
    return embedder


async def test_gemini_embedder_embed_text():
    embedder = _make_embedder()
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=create_mock_response([[0.1, 0.2, 0.3]])
    )

    result = await embedder.embed_text(["test"])

    assert result == [[0.1, 0.2, 0.3]]
    embedder.client.aio.models.embed_content.assert_called_once()


async def test_gemini_embedder_embed_text_multiple():
    embedder = _make_embedder()
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=create_mock_response([[0.1, 0.2], [0.3, 0.4]])
    )

    result = await embedder.embed_text(["hello", "world"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]


async def test_gemini_embedder_get_vector_size_with_dimensionality():
    options = GeminiEmbedderOptions(output_dimensionality=768)
    embedder = _make_embedder(default_options=options)

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 768


async def test_gemini_embedder_get_vector_size_with_none_dimensionality():
    options = GeminiEmbedderOptions(output_dimensionality=None)
    embedder = _make_embedder(default_options=options)
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=create_mock_response([[0.1, 0.2, 0.3, 0.4, 0.5]])
    )

    vector_size = await embedder.get_vector_size()

    assert vector_size.size == 5
    assert vector_size.is_sparse is False


async def test_gemini_embedder_get_vector_size_with_not_given_dimensionality():
    options = GeminiEmbedderOptions(output_dimensionality=NOT_GIVEN)
    embedder = _make_embedder(default_options=options)
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=create_mock_response([[0.1, 0.2, 0.3]])
    )

    vector_size = await embedder.get_vector_size()

    assert vector_size.size == 3
    assert vector_size.is_sparse is False


async def test_gemini_embedder_get_vector_size_fallback_to_sample():
    embedder = _make_embedder()
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=create_mock_response([[0.1, 0.2, 0.3, 0.4]])
    )

    vector_size = await embedder.get_vector_size()

    embedder.client.aio.models.embed_content.assert_called_once()
    assert vector_size.size == 4
    assert vector_size.is_sparse is False


async def test_gemini_embedder_empty_response():
    embedder = _make_embedder()
    mock_response = MagicMock()
    mock_response.embeddings = []
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=mock_response
    )

    with pytest.raises(EmbeddingEmptyResponseError):
        await embedder.embed_text(["test"])


async def test_gemini_embedder_api_call_error():
    embedder = _make_embedder()

    class MockGoogleAPICallError(Exception):
        def __init__(self, message: str, code: int) -> None:
            super().__init__(message)
            self.code = code

    exc = MockGoogleAPICallError("Not found", 404)
    embedder.client.aio.models.embed_content = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

    with patch("ragbits.core.embeddings.dense.gemini.google_exceptions") as mock_google_exc:
        mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
        mock_google_exc.GoogleAPIError = Exception
        with pytest.raises(EmbeddingStatusError) as exc_info:
            await embedder.embed_text(["test"])

    assert exc_info.value.status_code == 404


async def test_gemini_embedder_generic_api_error():
    embedder = _make_embedder()

    class MockGoogleAPIError(Exception):
        pass

    class MockGoogleAPICallError(MockGoogleAPIError):
        pass

    exc = MockGoogleAPIError("Connection failed")
    embedder.client.aio.models.embed_content = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

    with patch("ragbits.core.embeddings.dense.gemini.google_exceptions") as mock_google_exc:
        mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
        mock_google_exc.GoogleAPIError = MockGoogleAPIError
        with pytest.raises(EmbeddingConnectionError):
            await embedder.embed_text(["test"])


async def test_gemini_embedder_with_task_type():
    options = GeminiEmbedderOptions(task_type="RETRIEVAL_DOCUMENT")
    embedder = _make_embedder(default_options=options)
    embedder.client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        return_value=create_mock_response([[0.1, 0.2]])
    )

    await embedder.embed_text(["test"])

    call_kwargs = embedder.client.aio.models.embed_content.call_args.kwargs
    assert call_kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"
