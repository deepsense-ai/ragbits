from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.noop import NoopEmbedder


async def test_noop_embedder_get_vector_size():
    """Test NoopEmbedder get_vector_size method."""
    embedder = NoopEmbedder()

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    # NoopEmbedder has default return values with 2-dimensional vectors [0.1, 0.1]
    assert vector_size.size == 2


async def test_noop_embedder_get_vector_size_custom_return_values():
    """Test NoopEmbedder get_vector_size with custom return values."""
    custom_return_values = [
        [[1.0, 2.0, 3.0, 4.0, 5.0]],  # 5-dimensional vector
        [[6.0, 7.0, 8.0, 9.0, 10.0]],
    ]
    embedder = NoopEmbedder(return_values=custom_return_values)

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 5


async def test_noop_embedder_embed_text_consistency():
    """Test that get_vector_size is consistent with actual embeddings."""
    embedder = NoopEmbedder()

    # Get vector size
    vector_size = await embedder.get_vector_size()

    # Get actual embeddings
    embeddings = await embedder.embed_text(["test text"])

    # Check consistency
    assert len(embeddings[0]) == vector_size.size


async def test_noop_embedder_embed_text_consistency_custom():
    """Test consistency with custom return values."""
    custom_return_values = [
        [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]],  # 7-dimensional vector
    ]
    embedder = NoopEmbedder(return_values=custom_return_values)

    # Get vector size
    vector_size = await embedder.get_vector_size()

    # Get actual embeddings
    embeddings = await embedder.embed_text(["test text"])

    # Check consistency
    assert len(embeddings[0]) == vector_size.size == 7
