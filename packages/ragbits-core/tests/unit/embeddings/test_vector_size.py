from ragbits.core.embeddings.base import VectorSize


def test_vector_size_creation():
    """Test basic VectorSize creation with default values."""
    vector_size = VectorSize(size=384)

    assert vector_size.size == 384
    assert vector_size.is_sparse is False


def test_vector_size_creation_sparse():
    """Test VectorSize creation for sparse vectors."""
    vector_size = VectorSize(size=50000, is_sparse=True)

    assert vector_size.size == 50000
    assert vector_size.is_sparse is True


def test_vector_size_creation_dense():
    """Test VectorSize creation for dense vectors explicitly."""
    vector_size = VectorSize(size=768, is_sparse=False)

    assert vector_size.size == 768
    assert vector_size.is_sparse is False


def test_vector_size_equality():
    """Test VectorSize equality comparison."""
    vector_size1 = VectorSize(size=384, is_sparse=False)
    vector_size2 = VectorSize(size=384, is_sparse=False)
    vector_size3 = VectorSize(size=384, is_sparse=True)
    vector_size4 = VectorSize(size=768, is_sparse=False)

    assert vector_size1 == vector_size2
    assert vector_size1 != vector_size3
    assert vector_size1 != vector_size4


def test_vector_size_repr():
    """Test VectorSize string representation."""
    vector_size = VectorSize(size=384, is_sparse=False)
    repr_str = repr(vector_size)

    assert "384" in repr_str
    assert "is_sparse=False" in repr_str


def test_vector_size_dict_conversion():
    """Test VectorSize conversion to/from dict."""
    vector_size = VectorSize(size=1024, is_sparse=True)

    # Test model_dump (to dict)
    vector_dict = vector_size.model_dump()
    expected_dict = {"size": 1024, "is_sparse": True}
    assert vector_dict == expected_dict

    # Test model_validate (from dict)
    reconstructed = VectorSize.model_validate(vector_dict)
    assert reconstructed == vector_size
