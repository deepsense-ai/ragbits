from unittest.mock import patch

import pytest

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.vertex_multimodal import VertexAIMultimodelEmbedder


async def test_vertex_multimodal_get_vector_size():
    """Test VertexAI multimodal embedder get_vector_size method."""
    embedder = VertexAIMultimodelEmbedder(model_name="multimodalembedding@001")

    # Mock the embedding call - _embed returns a list of dicts with "embedding" key
    with patch.object(embedder, "_embed") as mock_embed:
        mock_embed.return_value = [{"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}]

        vector_size = await embedder.get_vector_size()

        assert isinstance(vector_size, VectorSize)
        assert vector_size.is_sparse is False
        assert vector_size.size == 5


async def test_vertex_multimodal_get_vector_size_consistency():
    """Test that get_vector_size is consistent with actual embeddings."""
    embedder = VertexAIMultimodelEmbedder(model_name="multimodalembedding@001")

    # Mock the embedding call to return consistent dimensions
    with patch.object(embedder, "_embed") as mock_embed:
        mock_embedding_vector = [0.1] * 1408  # Typical dimension for multimodal embeddings
        mock_embed.return_value = [{"embedding": mock_embedding_vector}]

        # Get vector size
        vector_size = await embedder.get_vector_size()

        # Get actual embeddings
        embeddings = await embedder.embed_text(["test text"])

        # Check consistency
        assert len(embeddings[0]) == vector_size.size == 1408


async def test_vertex_multimodal_get_vector_size_different_dimensions():
    """Test VertexAI multimodal embedder with different embedding dimensions."""
    embedder = VertexAIMultimodelEmbedder(model_name="multimodalembedding@001")

    # Mock the embedding call with different dimensions
    with patch.object(embedder, "_embed") as mock_embed:
        mock_embed.return_value = [
            {"embedding": [0.1] * 768}  # Different dimension
        ]

        vector_size = await embedder.get_vector_size()

        assert isinstance(vector_size, VectorSize)
        assert vector_size.is_sparse is False
        assert vector_size.size == 768


def test_vertex_multimodal_unsupported_model():
    """Test that VertexAI multimodal embedder raises error for unsupported models."""
    with pytest.raises(ValueError, match="Model unsupported-model is not supported"):
        VertexAIMultimodelEmbedder(model_name="unsupported-model")


async def test_vertex_multimodal_embed_text_calls_get_vector_size():
    """Test that embed_text and get_vector_size use the same underlying mechanism."""
    embedder = VertexAIMultimodelEmbedder(model_name="multimodalembedding@001")

    # Mock the _embed method
    with patch.object(embedder, "_embed") as mock_embed:
        mock_embed.return_value = [{"embedding": [0.1, 0.2, 0.3]}]

        # Call both methods
        vector_size = await embedder.get_vector_size()
        embeddings = await embedder.embed_text(["test"])

        # Both should call _embed
        assert mock_embed.call_count == 2
        assert vector_size.size == len(embeddings[0])
