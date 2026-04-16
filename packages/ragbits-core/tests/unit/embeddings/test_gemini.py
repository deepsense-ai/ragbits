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


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_embed_text(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.embed_content = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3]]))
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    embedder = GeminiEmbedder(model_name="text-embedding-004")
    result = await embedder.embed_text(["test"])

    assert result == [[0.1, 0.2, 0.3]]
    mock_models.embed_content.assert_called_once()


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_embed_text_multiple(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.embed_content = AsyncMock(return_value=create_mock_response([[0.1, 0.2], [0.3, 0.4]]))
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    embedder = GeminiEmbedder(model_name="text-embedding-004")
    result = await embedder.embed_text(["hello", "world"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_get_vector_size_with_dimensionality(mock_genai):
    options = GeminiEmbedderOptions(output_dimensionality=768)
    embedder = GeminiEmbedder(model_name="text-embedding-004", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 768


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_get_vector_size_with_none_dimensionality(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.embed_content = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3, 0.4, 0.5]]))
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    options = GeminiEmbedderOptions(output_dimensionality=None)
    embedder = GeminiEmbedder(model_name="text-embedding-004", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert vector_size.size == 5
    assert vector_size.is_sparse is False


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_get_vector_size_with_not_given_dimensionality(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.embed_content = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3]]))
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    options = GeminiEmbedderOptions(output_dimensionality=NOT_GIVEN)
    embedder = GeminiEmbedder(model_name="text-embedding-004", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert vector_size.size == 3
    assert vector_size.is_sparse is False


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_get_vector_size_fallback_to_sample(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.embed_content = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3, 0.4]]))
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    embedder = GeminiEmbedder(model_name="text-embedding-004")

    vector_size = await embedder.get_vector_size()

    mock_models.embed_content.assert_called_once()
    assert vector_size.size == 4
    assert vector_size.is_sparse is False


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_empty_response(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = []
    mock_models.embed_content = AsyncMock(return_value=mock_response)
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    embedder = GeminiEmbedder(model_name="text-embedding-004")

    with pytest.raises(EmbeddingEmptyResponseError):
        await embedder.embed_text(["test"])


@patch("ragbits.core.embeddings.dense.gemini.genai")
@patch("ragbits.core.embeddings.dense.gemini.google_exceptions")
async def test_gemini_embedder_api_call_error(mock_google_exc, mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()

    # Create a real-ish exception
    exc = Exception("Not found")
    exc.code = 404
    mock_google_exc.GoogleAPICallError = type(exc)
    mock_google_exc.GoogleAPIError = Exception
    mock_models.embed_content = AsyncMock(side_effect=exc)
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    embedder = GeminiEmbedder(model_name="text-embedding-004")

    with pytest.raises(EmbeddingStatusError) as exc_info:
        await embedder.embed_text(["test"])
    assert exc_info.value.status_code == 404


@patch("ragbits.core.embeddings.dense.gemini.genai")
@patch("ragbits.core.embeddings.dense.gemini.google_exceptions")
async def test_gemini_embedder_generic_api_error(mock_google_exc, mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()

    # GoogleAPIError that is NOT a GoogleAPICallError
    class MockGoogleAPIError(Exception):
        pass

    class MockGoogleAPICallError(MockGoogleAPIError):
        pass

    exc = MockGoogleAPIError("Connection failed")
    mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
    mock_google_exc.GoogleAPIError = MockGoogleAPIError
    mock_models.embed_content = AsyncMock(side_effect=exc)
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    embedder = GeminiEmbedder(model_name="text-embedding-004")

    with pytest.raises(EmbeddingConnectionError):
        await embedder.embed_text(["test"])


@patch("ragbits.core.embeddings.dense.gemini.genai")
async def test_gemini_embedder_with_task_type(mock_genai):
    mock_client = MagicMock()
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.embed_content = AsyncMock(return_value=create_mock_response([[0.1, 0.2]]))
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    mock_genai.Client.return_value = mock_client

    options = GeminiEmbedderOptions(task_type="RETRIEVAL_DOCUMENT")
    embedder = GeminiEmbedder(model_name="text-embedding-004", default_options=options)

    await embedder.embed_text(["test"])

    call_kwargs = mock_models.embed_content.call_args.kwargs
    assert call_kwargs["config"]["task_type"] == "RETRIEVAL_DOCUMENT"
