import pytest

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.sparse.bag_of_tokens import BagOfTokens, BagOfTokensOptions


async def test_bag_of_tokens_get_vector_size_with_encoding():
    """Test BagOfTokens get_vector_size method with encoding_name."""
    embedder = BagOfTokens(encoding_name="cl100k_base")

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is True
    assert vector_size.size > 0  # Should have a positive vocabulary size
    assert vector_size.size == 100277  # cl100k_base has a vocabulary size of 100277


async def test_bag_of_tokens_get_vector_size_with_model():
    """Test BagOfTokens get_vector_size method with model_name."""
    embedder = BagOfTokens(model_name="gpt-3.5-turbo")

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is True
    assert vector_size.size > 0  # Should have a positive vocabulary size
    assert vector_size.size == 100277  # gpt-3.5-turbo uses cl100k_base encoding


async def test_bag_of_tokens_get_vector_size_default():
    """Test BagOfTokens get_vector_size method with default model (gpt-4o)."""
    embedder = BagOfTokens()

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is True
    assert vector_size.size > 0  # Should have a positive vocabulary size


async def test_bag_of_tokens_get_vector_size_error_both_specified():
    """Test BagOfTokens get_vector_size raises error when both encoding_name and model_name are specified."""
    with pytest.raises(ValueError, match="Please specify only one of encoding_name or model_name"):
        BagOfTokens(encoding_name="cl100k_base", model_name="gpt-3.5-turbo")


async def test_bag_of_tokens_get_vector_size_error_none_specified():
    """Test BagOfTokens get_vector_size raises error when neither encoding_name nor model_name are specified."""
    # This test is no longer valid since we now default to gpt-4o when nothing is specified
    # The constructor will automatically use gpt-4o as default
    embedder = BagOfTokens()
    vector_size = await embedder.get_vector_size()
    assert vector_size.size > 0  # Should succeed with default gpt-4o


async def test_bag_of_tokens_embed_text_consistency():
    """Test that BagOfTokens embeddings are consistent with vector size."""
    embedder = BagOfTokens(encoding_name="cl100k_base")

    # Get vector size
    vector_size = await embedder.get_vector_size()

    # Get actual embeddings
    embeddings = await embedder.embed_text(["test text"])

    # For sparse embeddings, all indices should be within the vocabulary size
    for embedding in embeddings:
        assert all(idx < vector_size.size for idx in embedding.indices)
        assert all(idx >= 0 for idx in embedding.indices)


async def test_bag_of_tokens_different_encodings():
    """Test BagOfTokens with different encodings have different vocabulary sizes."""
    embedder1 = BagOfTokens(encoding_name="cl100k_base")
    embedder2 = BagOfTokens(encoding_name="p50k_base")

    vector_size1 = await embedder1.get_vector_size()
    vector_size2 = await embedder2.get_vector_size()

    assert vector_size1.size != vector_size2.size
    assert vector_size1.is_sparse is True
    assert vector_size2.is_sparse is True


async def test_bag_of_tokens_min_token_count_option():
    """Test BagOfTokens with min_token_count option."""
    embedder = BagOfTokens(encoding_name="cl100k_base")
    options = BagOfTokensOptions(min_token_count=2)

    # Test with text that has some repeated tokens
    embeddings = await embedder.embed_text(["test test test"], options=options)

    # Should have embeddings (non-empty vectors)
    assert len(embeddings) == 1
    assert len(embeddings[0].indices) > 0
    assert len(embeddings[0].values) > 0
