from unittest.mock import MagicMock, patch

import pytest

from ragbits.core.vector_store.base import VectorDBEntry
from ragbits.core.vector_store.chromadb_store import ChromaDBStore


@pytest.fixture
def mock_chromadb_store():
    return ChromaDBStore(
        client=MagicMock(),
        index_name="test_index",
    )


def test_chromadbstore_init_import_error():
    with patch("ragbits.core.vector_store.chromadb_store.HAS_CHROMADB", False), pytest.raises(ImportError):
        ChromaDBStore(
            client=MagicMock(),
            index_name="test_index",
        )


def test_get_chroma_collection(mock_chromadb_store: ChromaDBStore):
    _ = mock_chromadb_store._get_chroma_collection()
    assert mock_chromadb_store._client.get_or_create_collection.call_count == 2  # type: ignore


async def test_stores_entries_correctly(mock_chromadb_store: ChromaDBStore):
    data = [
        VectorDBEntry(
            key="test_key",
            vector=[0.1, 0.2, 0.3],
            metadata={
                "content": "test content",
                "document": {
                    "title": "test title",
                    "source": {"path": "/test/path"},
                    "document_type": "test_type",
                },
            },
        )
    ]

    await mock_chromadb_store.store(data)

    mock_chromadb_store._client.get_or_create_collection().add.assert_called_once()  # type: ignore
    mock_chromadb_store._client.get_or_create_collection().add.assert_called_with(  # type: ignore
        ids=["92488e1e3eeecdf99f3ed2ce59233efb4b4fb612d5655c0ce9ea52b5a502e655"],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[
            {
                "__key": "test_key",
                "__metadata": '{"content": "test content", "document": {"title": "test title", "source":'
                ' {"path": "/test/path"}, "document_type": "test_type"}}',
            }
        ],
    )


async def test_retrieves_entries_correctly(mock_chromadb_store: ChromaDBStore):
    vector = [0.1, 0.2, 0.3]
    mock_collection = mock_chromadb_store._get_chroma_collection()
    mock_collection.query.return_value = {  # type: ignore
        "metadatas": [
            [
                {
                    "__key": "test_key",
                    "__metadata": '{"content": "test content", "document": {"title": "test title", "source":'
                    ' {"path": "/test/path-1"}, "document_type": "txt"}}',
                },
            ]
        ],
        "embeddings": [[[0.12, 0.25, 0.29]]],
        "distances": [[0.1]],
    }

    entries = await mock_chromadb_store.retrieve(vector)

    assert len(entries) == 1
    assert entries[0].metadata["content"] == "test content"
    assert entries[0].metadata["document"]["title"] == "test title"
    assert entries[0].vector == [0.12, 0.25, 0.29]


async def test_lists_entries_correctly(mock_chromadb_store: ChromaDBStore):
    mock_collection = mock_chromadb_store._get_chroma_collection()
    mock_collection.get.return_value = {  # type: ignore
        "metadatas": [
            {
                "__key": "test_key",
                "__metadata": '{"content": "test content", "document": {"title": "test title", "source":'
                ' {"path": "/test/path"}, "document_type": "test_type"}}',
            },
            {
                "__key": "test_key_2",
                "__metadata": '{"content": "test content 2", "document": {"title": "test title 2", "source":'
                ' {"path": "/test/path"}, "document_type": "test_type"}}',
            },
        ],
        "embeddings": [[0.12, 0.25, 0.29], [0.13, 0.26, 0.30]],
    }

    entries = await mock_chromadb_store.list()

    assert len(entries) == 2
    assert entries[0].metadata["content"] == "test content"
    assert entries[0].metadata["document"]["title"] == "test title"
    assert entries[0].vector == [0.12, 0.25, 0.29]
    assert entries[1].metadata["content"] == "test content 2"
    assert entries[1].metadata["document"]["title"] == "test title 2"
    assert entries[1].vector == [0.13, 0.26, 0.30]
