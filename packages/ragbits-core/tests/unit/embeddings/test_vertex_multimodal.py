import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.vertex_multimodal import (
    VertexAIMultimodalEmbedder,
    VertexAIMultimodalEmbedderOptions,
)
from ragbits.core.embeddings.exceptions import (
    EmbeddingConnectionError,
    EmbeddingResponseError,
    EmbeddingStatusError,
)


@pytest.fixture(autouse=True)
def mock_genai_types():
    mock_types = MagicMock()
    with patch("ragbits.core.embeddings.dense.vertex_multimodal.genai_types", mock_types):
        yield mock_types


# --- Tests using _embed mock (work for both model families) ---


async def test_get_vector_size():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    with patch.object(embedder, "_embed") as mock_embed:
        mock_embed.return_value = [{"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}]
        vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 5


async def test_get_vector_size_consistency():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    with patch.object(embedder, "_embed") as mock_embed:
        mock_embedding_vector = [0.1] * 1408
        mock_embed.return_value = [{"embedding": mock_embedding_vector}]

        vector_size = await embedder.get_vector_size()
        embeddings = await embedder.embed_text(["test text"])

    assert len(embeddings[0]) == vector_size.size == 1408


async def test_embed_text_calls_embed():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    with patch.object(embedder, "_embed") as mock_embed:
        mock_embed.return_value = [{"embedding": [0.1, 0.2, 0.3]}]

        vector_size = await embedder.get_vector_size()
        embeddings = await embedder.embed_text(["test"])

    assert mock_embed.call_count == 2
    assert vector_size.size == len(embeddings[0])


def test_image_support():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")
    assert embedder.image_support() is True


def test_is_legacy_model():
    legacy = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")
    assert legacy._is_legacy_model is True


def test_is_modern_model():
    modern = _make_modern_embedder(model_name="gemini-embedding-exp-03-07")
    assert modern._is_legacy_model is False


def test_concurrency_param():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001", concurrency=5)
    assert embedder.concurrency == 5


def test_concurrency_must_be_positive():
    with pytest.raises(ValueError, match="concurrency must be >= 1"):
        VertexAIMultimodalEmbedder(model_name="multimodalembedding@001", concurrency=0)


# --- Modern model helpers ---


def _make_modern_embedder(model_name: str = "gemini-embedding-exp-03-07") -> VertexAIMultimodalEmbedder:
    """Create a modern VertexAIMultimodalEmbedder with a stub client (no real google-genai SDK needed)."""
    mock_client = MagicMock()
    with (
        patch("ragbits.core.embeddings.dense.vertex_multimodal.HAS_GOOGLE_GENAI", True),
        patch("ragbits.core.embeddings.dense.vertex_multimodal.genai", create=True) as mock_genai,
    ):
        mock_genai.Client.return_value = mock_client
        embedder = VertexAIMultimodalEmbedder(model_name=model_name)
    return embedder


# --- Modern model tests (gemini-embedding-*) ---


async def test_modern_embed_text():
    embedder = _make_modern_embedder()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]
    embedder._client.aio.models.embed_content = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

    result = await embedder.embed_text(["test"])

    assert result == [[0.1, 0.2, 0.3]]
    embedder._client.aio.models.embed_content.assert_called_once()


async def test_modern_embed_multiple_texts():
    embedder = _make_modern_embedder()

    def make_response(values: list[float]) -> MagicMock:
        mock_response = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = values
        mock_response.embeddings = [mock_embedding]
        return mock_response

    embedder._client.aio.models.embed_content = AsyncMock(  # type: ignore[method-assign]
        side_effect=[make_response([0.1, 0.2]), make_response([0.3, 0.4])]
    )

    result = await embedder.embed_text(["hello", "world"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]


async def test_modern_omits_none_dimensions_in_config():
    embedder = _make_modern_embedder()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]
    embedder._client.aio.models.embed_content = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

    options = VertexAIMultimodalEmbedderOptions(dimensions=None)
    await embedder.embed_text(["test"], options=options)

    assert embedder._client.aio.models.embed_content.call_args.kwargs["config"] is None


async def test_modern_timeout_error_mapped_to_embedding_connection_error():
    embedder = _make_modern_embedder()

    async def slow_embed(*args, **kwargs) -> MagicMock:  # noqa: ARG001
        await asyncio.sleep(1.2)
        return MagicMock(embeddings=[MagicMock(values=[0.1, 0.2, 0.3])])

    embedder._client.aio.models.embed_content = AsyncMock(side_effect=slow_embed)  # type: ignore[method-assign]

    options = VertexAIMultimodalEmbedderOptions(timeout=1)
    with pytest.raises(EmbeddingConnectionError, match="Request timed out"):
        await embedder.embed_text(["test"], options=options)


async def test_modern_empty_response():
    embedder = _make_modern_embedder()
    mock_response = MagicMock()
    mock_response.embeddings = []
    embedder._client.aio.models.embed_content = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

    with pytest.raises(EmbeddingResponseError):
        await embedder.embed_text(["test"])


async def test_modern_api_call_error():
    embedder = _make_modern_embedder()

    class MockGoogleAPICallError(Exception):
        def __init__(self, message: str, code: int) -> None:
            super().__init__(message)
            self.code = code

    exc = MockGoogleAPICallError("Not found", 404)
    embedder._client.aio.models.embed_content = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

    with patch("ragbits.core.embeddings.dense.vertex_multimodal.google_exceptions") as mock_google_exc:
        mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
        mock_google_exc.GoogleAPIError = Exception
        with pytest.raises(EmbeddingStatusError) as exc_info:
            await embedder.embed_text(["test"])

    assert exc_info.value.status_code == 404


async def test_modern_connection_error():
    embedder = _make_modern_embedder()

    class MockGoogleAPIError(Exception):
        pass

    class MockGoogleAPICallError(MockGoogleAPIError):
        pass

    exc = MockGoogleAPIError("Connection failed")
    embedder._client.aio.models.embed_content = AsyncMock(side_effect=exc)  # type: ignore[method-assign]

    with patch("ragbits.core.embeddings.dense.vertex_multimodal.google_exceptions") as mock_google_exc:
        mock_google_exc.GoogleAPICallError = MockGoogleAPICallError
        mock_google_exc.GoogleAPIError = MockGoogleAPIError
        with pytest.raises(EmbeddingConnectionError):
            await embedder.embed_text(["test"])


async def test_modern_invalid_image_payload_mapped_to_embedding_response_error():
    embedder = _make_modern_embedder()

    with pytest.raises(EmbeddingResponseError, match="Invalid base64-encoded image payload"):
        await embedder._embed([{"image": {"bytesBase64Encoded": "%%%"}}])


# --- Legacy model tests (multimodalembedding*) ---


async def test_legacy_embed_text():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    mock_response = [{"embedding": [0.1, 0.2, 0.3]}]
    with patch.object(embedder, "_embed_legacy", new_callable=AsyncMock, return_value=mock_response):
        result = await embedder.embed_text(["test"])

    assert result == [[0.1, 0.2, 0.3]]


async def test_legacy_embed_image():
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    mock_response = [{"embedding": [0.4, 0.5, 0.6]}]
    with patch.object(embedder, "_embed_legacy", new_callable=AsyncMock, return_value=mock_response):
        result = await embedder.embed_image([b"\x89PNG\r\n\x1a\n"])

    assert result == [[0.4, 0.5, 0.6]]


@patch("ragbits.core.embeddings.dense.vertex_multimodal.google.auth")
@patch("ragbits.core.embeddings.dense.vertex_multimodal.aiohttp.ClientSession")
async def test_legacy_embed_http_call(mock_session_cls: MagicMock, mock_google_auth: MagicMock):
    # Mock google.auth.default()
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"  # noqa: S105
    mock_credentials.valid = True
    mock_google_auth.default.return_value = (mock_credentials, "test-project")

    # Mock aiohttp response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"predictions": [{"textEmbedding": [0.1, 0.2, 0.3]}]})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = mock_session

    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")
    result = await embedder.embed_text(["test"])

    assert result == [[0.1, 0.2, 0.3]]
    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "multimodalembedding@001:predict" in call_kwargs.args[0]
    assert call_kwargs.kwargs["json"] == {"instances": [{"text": "test"}]}


@patch("ragbits.core.embeddings.dense.vertex_multimodal.google.auth")
@patch("ragbits.core.embeddings.dense.vertex_multimodal.aiohttp.ClientSession")
async def test_legacy_embed_http_error(mock_session_cls: MagicMock, mock_google_auth: MagicMock):
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"  # noqa: S105
    mock_credentials.valid = True
    mock_google_auth.default.return_value = (mock_credentials, "test-project")

    mock_response = MagicMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad request")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = mock_session

    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    with pytest.raises(EmbeddingStatusError) as exc_info:
        await embedder.embed_text(["test"])
    assert exc_info.value.status_code == 400


@patch("ragbits.core.embeddings.dense.vertex_multimodal.google.auth")
async def test_legacy_auth_failure_mapped_to_embedding_connection_error(mock_google_auth: MagicMock):
    mock_google_auth.default.side_effect = Exception("No ADC")
    embedder = VertexAIMultimodalEmbedder(model_name="multimodalembedding@001")

    with pytest.raises(EmbeddingConnectionError, match="Failed to authenticate with Google Cloud"):
        await embedder.embed_text(["test"])
