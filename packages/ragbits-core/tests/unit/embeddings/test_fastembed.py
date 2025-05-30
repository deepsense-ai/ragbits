import pickle

from ragbits.core.embeddings.base import VectorSize
from ragbits.core.embeddings.dense.fastembed import FastEmbedEmbedder
from ragbits.core.embeddings.sparse.fastembed import FastEmbedSparseEmbedder


async def test_fastembed_dense_embeddings():
    embeddings = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")
    result = await embeddings.embed_text(["text1"])
    assert len(result[0]) == 384


async def test_fastembed_dense_get_vector_size():
    """Test FastEmbedEmbedder get_vector_size method."""
    embedder = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is False
    assert vector_size.size == 384  # Expected dimension for bge-small-en-v1.5


async def test_fastembed_dense_get_vector_size_consistency():
    """Test that get_vector_size is consistent with actual embeddings."""
    embedder = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")

    # Get vector size
    vector_size = await embedder.get_vector_size()

    # Get actual embeddings
    embeddings = await embedder.embed_text(["test text"])

    # Check consistency
    assert len(embeddings[0]) == vector_size.size


async def test_fastembed_sparse_embeddings():
    embeddings = FastEmbedSparseEmbedder("qdrant/bm25")
    result = await embeddings.embed_text(["text1"])
    assert len(result[0].values) == len(result[0].indices)


async def test_fastembed_sparse_get_vector_size():
    """Test FastEmbedSparseEmbedder get_vector_size method."""
    embedder = FastEmbedSparseEmbedder("qdrant/bm25")

    vector_size = await embedder.get_vector_size()

    assert isinstance(vector_size, VectorSize)
    assert vector_size.is_sparse is True
    assert vector_size.size > 0  # Should have a positive vocabulary size


async def test_fastembed_sparse_get_vector_size_consistency():
    """Test that sparse get_vector_size returns vocabulary size."""
    embedder = FastEmbedSparseEmbedder("qdrant/bm25")

    vector_size = await embedder.get_vector_size()

    # For sparse embeddings, the size should represent the vocabulary size
    # which should be much larger than typical dense embedding dimensions
    assert vector_size.size > 1000  # Vocabulary should be reasonably large
    assert vector_size.is_sparse is True


def test_fastembed_dense_pickling():
    embeddings = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")
    pickled = pickle.dumps(embeddings)
    unpickled = pickle.loads(pickled)  # noqa: S301
    assert isinstance(unpickled, FastEmbedEmbedder)
    assert unpickled.model_name == "BAAI/bge-small-en-v1.5"
    assert unpickled.default_options == embeddings.default_options
    assert unpickled.use_gpu == embeddings.use_gpu


def test_fastembed_sparse_pickling():
    embeddings = FastEmbedSparseEmbedder("qdrant/bm25")
    pickled = pickle.dumps(embeddings)
    unpickled = pickle.loads(pickled)  # noqa: S301
    assert isinstance(unpickled, FastEmbedSparseEmbedder)
    assert unpickled.model_name == "qdrant/bm25"
    assert unpickled.default_options == embeddings.default_options
    assert unpickled.use_gpu == embeddings.use_gpu
