from unittest.mock import MagicMock, patch

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.litellm import LiteLLMEmbedder, LiteLLMEmbedderOptions
from ragbits.core.types import NOT_GIVEN


def create_mock_response(embeddings_data: list[list[float]]) -> MagicMock:
    """Create a mock response object that mimics the LiteLLM response structure."""
    mock_response = MagicMock()
    mock_response.data = [{"embedding": embedding} for embedding in embeddings_data]
    mock_response.usage = None
    return mock_response


async def test_litellm_embedder_get_vector_size_with_dimensions():
    """Test LiteLLMEmbedder get_vector_size when dimensions are specified in options."""
    options = LiteLLMEmbedderOptions(dimensions=1536)
    embedder = LiteLLMEmbedder(model_name="text-embedding-ada-002", default_options=options)

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 1536


async def test_litellm_embedder_get_vector_size_with_none_dimensions():
    """Test LiteLLMEmbedder get_vector_size when dimensions is None."""
    options = LiteLLMEmbedderOptions(dimensions=None)
    embedder = LiteLLMEmbedder(model_name="text-embedding-ada-002", default_options=options)

    with patch("ragbits.core.embeddings.dense.litellm.litellm.aembedding") as mock_embedding:
        mock_response = create_mock_response([[0.1, 0.2, 0.3, 0.4, 0.5]])
        mock_embedding.return_value = mock_response

        vector_size = await embedder.get_vector_size()

        assert isinstance(vector_size, VectorSize)
        assert vector_size.is_sparse is False
        assert vector_size.size == 5


async def test_litellm_embedder_get_vector_size_with_not_given_dimensions():
    """Test LiteLLMEmbedder get_vector_size when dimensions is NOT_GIVEN."""
    options = LiteLLMEmbedderOptions(dimensions=NOT_GIVEN)
    embedder = LiteLLMEmbedder(model_name="text-embedding-ada-002", default_options=options)

    with patch("ragbits.core.embeddings.dense.litellm.litellm.aembedding") as mock_embedding:
        mock_response = create_mock_response([[0.1, 0.2, 0.3]])
        mock_embedding.return_value = mock_response

        vector_size = await embedder.get_vector_size()

        assert isinstance(vector_size, VectorSize)
        assert vector_size.is_sparse is False
        assert vector_size.size == 3


async def test_litellm_embedder_get_vector_size_no_default_options():
    """Test LiteLLMEmbedder get_vector_size when no default options are set."""
    embedder = LiteLLMEmbedder(model_name="text-embedding-ada-002")

    with patch("ragbits.core.embeddings.dense.litellm.litellm.aembedding") as mock_embedding:
        mock_response = create_mock_response([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]])
        mock_embedding.return_value = mock_response

        vector_size = await embedder.get_vector_size()

        assert isinstance(vector_size, VectorSize)
        assert vector_size.is_sparse is False
        assert vector_size.size == 8


async def test_litellm_embedder_get_vector_size_consistency():
    """Test that get_vector_size is consistent with actual embeddings."""
    options = LiteLLMEmbedderOptions(dimensions=512)
    embedder = LiteLLMEmbedder(model_name="text-embedding-ada-002", default_options=options)

    # Mock the embedding call
    with patch("ragbits.core.embeddings.dense.litellm.litellm.aembedding") as mock_embedding:
        # Create a mock embedding with 512 dimensions
        mock_embedding_vector = [0.1] * 512
        mock_response = create_mock_response([mock_embedding_vector])
        mock_embedding.return_value = mock_response

        # Get vector size
        vector_size = await embedder.get_vector_size()

        # Get actual embeddings
        embeddings = await embedder.embed_text(["test text"])

        # Check consistency
        assert len(embeddings[0]) == vector_size.size == 512


async def test_litellm_embedder_get_vector_size_fallback_to_sample():
    """Test that get_vector_size falls back to sampling when no dimensions specified."""
    embedder = LiteLLMEmbedder(model_name="text-embedding-ada-002")

    with patch("ragbits.core.embeddings.dense.litellm.litellm.aembedding") as mock_embedding:
        mock_response = create_mock_response([[0.1, 0.2, 0.3, 0.4]])
        mock_embedding.return_value = mock_response

        vector_size = await embedder.get_vector_size()

        # Should have called the embedding API to get sample
        mock_embedding.assert_called_once()
        assert vector_size.size == 4
        assert vector_size.is_sparse is False
