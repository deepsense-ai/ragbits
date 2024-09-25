from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ragbits.core.embeddings.base import Embeddings
from ragbits.core.vector_store.chromadb_store import ChromaDBStore, VectorDBEntry


@pytest.fixture
def mock_chroma_client():
    return MagicMock()


@pytest.fixture
def mock_embedding_function():
    return AsyncMock()


@pytest.fixture
def mock_chromadb_store(mock_chroma_client, mock_embedding_function):
    return ChromaDBStore(
        index_name="test_index",
        chroma_client=mock_chroma_client,
        embedding_function=mock_embedding_function,
    )


class MockEmbeddings(Embeddings):
    async def embed_text(self, text):
        return [[0.4, 0.5, 0.6]]

    def __call__(self, input):
        return self.embed_text(input)


@pytest.fixture
def custom_embedding_function():
    return MockEmbeddings()


@pytest.fixture
def mock_chromadb_store_with_custom_embedding_function(mock_chroma_client, custom_embedding_function):
    return ChromaDBStore(
        index_name="test_index",
        chroma_client=mock_chroma_client,
        embedding_function=custom_embedding_function,
    )


@pytest.fixture
def mock_vector_db_entry():
    return VectorDBEntry(
        key="test_key",
        vector=[0.1, 0.2, 0.3],
        metadata={
            "content": "test content",
            "document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"},
        },
    )


def test_chromadbstore_init_import_error():
    with patch("ragbits.document_search.vector_store.chromadb_store.HAS_CHROMADB", False):
        with pytest.raises(ImportError):
            ChromaDBStore(index_name="test_index", chroma_client=MagicMock(), embedding_function=MagicMock())


def test_get_chroma_collection(mock_chromadb_store):
    _ = mock_chromadb_store._get_chroma_collection()
    assert mock_chromadb_store._chroma_client.get_or_create_collection.called


def test_get_chroma_collection_with_custom_embedding_function(
    custom_embedding_function, mock_chromadb_store_with_custom_embedding_function, mock_chroma_client
):
    mock_chroma_client.get_or_create_collection.assert_called_once_with(
        name="test_index",
        metadata={"hnsw:space": "l2"},
    )


async def test_stores_entries_correctly(mock_chromadb_store):
    data = [
        VectorDBEntry(
            key="test_key",
            vector=[0.1, 0.2, 0.3],
            metadata={
                "content": "test content",
                "document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"},
            },
        )
    ]
    await mock_chromadb_store.store(data)
    mock_chromadb_store._chroma_client.get_or_create_collection().add.assert_called_once()


def test_process_db_entry(mock_chromadb_store, mock_vector_db_entry):
    id, embedding, text, metadata = mock_chromadb_store._process_db_entry(mock_vector_db_entry)
    print(f"metadata: {metadata}, type: {type(metadata)}")

    assert id == sha256(b"test_key").hexdigest()
    assert embedding == [0.1, 0.2, 0.3]
    assert text == "test content"
    assert (
        metadata["document"]
        == '{"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"}'
    )
    assert metadata["key"] == "test_key"


async def test_store(mock_chromadb_store, mock_vector_db_entry):
    await mock_chromadb_store.store([mock_vector_db_entry])
    assert mock_chromadb_store._chroma_client.get_or_create_collection().add.called


async def test_retrieves_entries_correctly(mock_chromadb_store):
    vector = [0.1, 0.2, 0.3]
    mock_collection = mock_chromadb_store._get_chroma_collection()
    mock_collection.query.return_value = {
        "documents": [["test content"]],
        "metadatas": [
            [
                {
                    "key": "test_key",
                    "content": "test content",
                    "document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"},
                }
            ]
        ],
    }
    entries = await mock_chromadb_store.retrieve(vector)
    assert len(entries) == 1
    assert entries[0].metadata["content"] == "test content"
    assert entries[0].metadata["document"]["title"] == "test title"


async def test_handles_empty_retrieve(mock_chromadb_store):
    vector = [0.1, 0.2, 0.3]
    mock_collection = mock_chromadb_store._get_chroma_collection()
    mock_collection.query.return_value = {"documents": [], "metadatas": []}
    entries = await mock_chromadb_store.retrieve(vector)
    assert len(entries) == 0


async def test_find_similar(mock_chromadb_store, mock_embedding_function):
    mock_embedding_function.embed_text.return_value = [[0.1, 0.2, 0.3]]
    mock_chromadb_store._embedding_function = mock_embedding_function
    mock_chromadb_store._chroma_client.get_or_create_collection().query.return_value = {
        "documents": [["test content"]],
        "distances": [[0.1]],
    }
    result = await mock_chromadb_store.find_similar("test text")
    assert result == "test content"


async def test_find_similar_with_custom_embeddings(mock_chromadb_store, custom_embedding_function):
    mock_chromadb_store._embedding_function = custom_embedding_function
    mock_chromadb_store._chroma_client.get_or_create_collection().query.return_value = {
        "documents": [["test content"]],
        "distances": [[0.1]],
    }
    result = await mock_chromadb_store.find_similar("test text")
    assert result == "test content"


def test_repr(mock_chromadb_store):
    assert repr(mock_chromadb_store) == "ChromaDBStore(index_name=test_index)"


@pytest.mark.parametrize(
    "retrieved, max_distance, expected",
    [
        ({"distances": [[0.1]], "documents": [["test content"]]}, None, "test content"),
        ({"distances": [[0.1]], "documents": [["test content"]]}, 0.2, "test content"),
        ({"distances": [[0.3]], "documents": [["test content"]]}, 0.2, None),
    ],
)
def test_return_best_match(mock_chromadb_store, retrieved, max_distance, expected):
    mock_chromadb_store._max_distance = max_distance
    result = mock_chromadb_store._return_best_match(retrieved)
    assert result == expected


def test_is_json_valid_string(mock_chromadb_store):
    # Arrange
    valid_json_string = '{"key": "value"}'

    # Act
    result = mock_chromadb_store._is_json(valid_json_string)

    # Assert
    assert result is True
