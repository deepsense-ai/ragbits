from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.openai import OpenAIEmbedder, OpenAIEmbedderOptions
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingEmptyResponseError,
    EmbeddingResponseError,
    EmbeddingStatusError,
)
from ragbits.core.types import NOT_GIVEN


def create_mock_response(embeddings_data: list[list[float]]) -> MagicMock:
    """Create a mock response object that mimics the OpenAI response structure."""
    mock_response = MagicMock()
    mock_embeddings = []
    for embedding in embeddings_data:
        mock_embedding = MagicMock()
        mock_embedding.embedding = embedding
        mock_embeddings.append(mock_embedding)
    mock_response.data = mock_embeddings
    mock_response.usage = None
    return mock_response


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_embed_text(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3]]))
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")
    result = await embedder.embed_text(["test"])

    assert result == [[0.1, 0.2, 0.3]]
    mock_client.embeddings.create.assert_called_once()


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_embed_text_multiple(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=create_mock_response([[0.1, 0.2], [0.3, 0.4]]))
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")
    result = await embedder.embed_text(["hello", "world"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_get_vector_size_with_dimensions(mock_openai_cls: MagicMock):
    mock_openai_cls.return_value = MagicMock()
    options = OpenAIEmbedderOptions(dimensions=1536)
    embedder = OpenAIEmbedder(model_name="text-embedding-3-small", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 1536


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_get_vector_size_with_none_dimensions(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3, 0.4, 0.5]]))
    mock_openai_cls.return_value = mock_client

    options = OpenAIEmbedderOptions(dimensions=None)
    embedder = OpenAIEmbedder(model_name="text-embedding-3-small", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert vector_size.size == 5
    assert vector_size.is_sparse is False


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_get_vector_size_with_not_given_dimensions(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3]]))
    mock_openai_cls.return_value = mock_client

    options = OpenAIEmbedderOptions(dimensions=NOT_GIVEN)
    embedder = OpenAIEmbedder(model_name="text-embedding-3-small", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert vector_size.size == 3
    assert vector_size.is_sparse is False


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_get_vector_size_fallback_to_sample(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=create_mock_response([[0.1, 0.2, 0.3, 0.4]]))
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")

    vector_size = await embedder.get_vector_size()

    mock_client.embeddings.create.assert_called_once()
    assert vector_size.size == 4
    assert vector_size.is_sparse is False


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_empty_response(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = []
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")

    with pytest.raises(EmbeddingEmptyResponseError):
        await embedder.embed_text(["test"])


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_connection_error(mock_openai_cls: MagicMock):
    import openai

    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(side_effect=openai.APIConnectionError(request=MagicMock()))
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")

    with pytest.raises(EmbeddingConnectionError):
        await embedder.embed_text(["test"])


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_status_error(mock_openai_cls: MagicMock):
    import openai

    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_client.embeddings.create = AsyncMock(
        side_effect=openai.APIStatusError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )
    )
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")

    with pytest.raises(EmbeddingStatusError) as exc_info:
        await embedder.embed_text(["test"])
    assert exc_info.value.status_code == 429


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_response_validation_error(mock_openai_cls: MagicMock):
    import openai

    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_client.embeddings.create = AsyncMock(
        side_effect=openai.APIResponseValidationError(
            response=mock_response,
            body=None,
        )
    )
    mock_openai_cls.return_value = mock_client

    embedder = OpenAIEmbedder(model_name="text-embedding-3-small")

    with pytest.raises(EmbeddingResponseError):
        await embedder.embed_text(["test"])


@patch("ragbits.core.embeddings.dense.openai.AsyncOpenAI")
async def test_openai_embedder_options_merge(mock_openai_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.embeddings = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=create_mock_response([[0.1, 0.2]]))
    mock_openai_cls.return_value = mock_client

    default_options = OpenAIEmbedderOptions(dimensions=256)
    embedder = OpenAIEmbedder(model_name="text-embedding-3-small", default_options=default_options)

    call_options = OpenAIEmbedderOptions(user="test-user")
    await embedder.embed_text(["test"], options=call_options)

    call_kwargs = mock_client.embeddings.create.call_args
    assert call_kwargs.kwargs["dimensions"] == 256
    assert call_kwargs.kwargs["user"] == "test-user"
