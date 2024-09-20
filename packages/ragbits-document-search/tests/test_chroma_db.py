from hashlib import sha256
import json
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import chromadb
import pytest

from ragbits.core.embeddings.base import Embeddings
from ragbits.document_search.vector_store.chromadb_store import ChromaDBStore, VectorDBEntry


@pytest.fixture
def mock_chroma_client():
    return MagicMock()


@pytest.fixture
def mock_embedding_function():
    return AsyncMock()


@pytest.fixture
def chroma_db_store(mock_chroma_client, mock_embedding_function):
    return ChromaDBStore(
        index_name="test_index",
        chroma_client=mock_chroma_client,
        embedding_function=mock_embedding_function,
    )


class MockEmbeddings(Embeddings):
    async def embed_text(self, text):
        return [[0.4, 0.5, 0.6]]


@pytest.fixture
def custom_embedding_function():
    return MockEmbeddings()


@pytest.fixture
def chromadb_store_with_custom_embedding_function(mock_chroma_client, custom_embedding_function):
    return ChromaDBStore(
        index_name="test_index",
        chroma_client=mock_chroma_client,
        embedding_function=custom_embedding_function,
    )


@pytest.fixture
def vector_db_entry():
    return VectorDBEntry(
        key="test_key",
        vector=[0.1, 0.2, 0.3],
        metadata={"content": "test content", "document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"}}
    )


def test_import_chromadb():
    with patch.dict('sys.modules', {'chromadb': None}):
        with pytest.raises(ImportError):
            import chromadb
    # from ragbits.document_search.vector_store.chromadb_store import HAS_CHROMADB
    # assert not HAS_CHROMADB
    

def test_chromadbstore_init_import_error():
    with patch('ragbits.document_search.vector_store.chromadb_store.HAS_CHROMADB', False):
        with pytest.raises(ImportError):
            ChromaDBStore(
                index_name="test_index",
                chroma_client=MagicMock(),
                embedding_function=MagicMock()
            )


def test_get_chroma_collection(chroma_db_store):
    _ = chroma_db_store._get_chroma_collection()
    assert chroma_db_store.chroma_client.get_or_create_collection.called


def test_get_chroma_collection_with_custom_embedding_function(custom_embedding_function, chromadb_store_with_custom_embedding_function, mock_chroma_client):
    collection_mock = MagicMock()
    mock_chroma_client.get_or_create_collection.return_value = chromadb.Collection(name="test_index",
                                                                                   id=str(uuid.uuid4()),
                                                                                   client=mock_chroma_client,
                                                                                   metadata={"hnsw:space": "l2"},
                                                                                   embedding_function=custom_embedding_function)

    result = chromadb_store_with_custom_embedding_function._get_chroma_collection()

    mock_chroma_client.get_or_create_collection.assert_called_once_with(
        name="test_index",
        metadata={"hnsw:space": "l2"},
        embedding_function=chromadb_store_with_custom_embedding_function.embedding_function
    )
    assert result == collection_mock


@pytest.mark.asyncio
async def test_stores_entries_correctly(chroma_db_store):
    data = [
        VectorDBEntry(
            key="test_key",
            vector=[0.1, 0.2, 0.3],
            metadata={"content": "test content", "document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"}},
        )
    ]
    await chroma_db_store.store(data)
    chroma_db_store.chroma_client.get_or_create_collection().add.assert_called_once()


def test_process_db_entry(chroma_db_store, vector_db_entry):
    id, embedding, text, metadata = chroma_db_store._process_db_entry(vector_db_entry)
    print(f"metadata: {metadata}, type: {type(metadata)}")

    assert id == sha256("test_key".encode("utf-8")).hexdigest()
    assert embedding == [0.1, 0.2, 0.3]
    assert text == "test content"
    assert metadata["document"] == '{"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"}'
    assert metadata["key"] == "test_key"


@pytest.mark.asyncio
async def test_store(chroma_db_store, vector_db_entry):
    await chroma_db_store.store([vector_db_entry])
    assert chroma_db_store.chroma_client.get_or_create_collection().add.called


@pytest.mark.asyncio
async def test_retrieves_entries_correctly(chroma_db_store):
    vector = [0.1, 0.2, 0.3]
    mock_collection = chroma_db_store._get_chroma_collection()
    mock_collection.query.return_value = {
        "documents": [["test content"]],
        "metadatas": [[{"key": "test_key", "content": "test content", "document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"}}]],
    }
    entries = await chroma_db_store.retrieve(vector)
    assert len(entries) == 1
    assert entries[0].metadata["content"] == "test content"
    assert entries[0].metadata["document"]["title"] == "test title"


@pytest.mark.asyncio
async def test_handles_empty_retrieve(chroma_db_store):
    vector = [0.1, 0.2, 0.3]
    mock_collection = chroma_db_store._get_chroma_collection()
    mock_collection.query.return_value = {"documents": [], "metadatas": []}
    entries = await chroma_db_store.retrieve(vector)
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_find_similar(chroma_db_store, mock_embedding_function):
    mock_embedding_function.embed_text.return_value = [[0.1, 0.2, 0.3]]
    chroma_db_store.embedding_function = mock_embedding_function
    chroma_db_store.chroma_client.get_or_create_collection().query.return_value = {
        "documents": [["test content"]],
        "distances": [[0.1]]
    }
    result = await chroma_db_store.find_similar("test text")
    assert result == "test content"


def test_repr(chroma_db_store):
    assert repr(chroma_db_store) == "ChromaDBStore(index_name=test_index)"