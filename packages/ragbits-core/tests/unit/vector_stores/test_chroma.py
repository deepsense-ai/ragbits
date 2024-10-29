from unittest.mock import MagicMock

import pytest

from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore


@pytest.fixture
def mock_chromadb_store() -> ChromaVectorStore:
    return ChromaVectorStore(
        client=MagicMock(),
        index_name="test_index",
    )


async def test_get_chroma_collection(mock_chromadb_store: ChromaVectorStore) -> None:
    _ = mock_chromadb_store._get_chroma_collection()
    assert mock_chromadb_store._client.get_or_create_collection.call_count == 2  # type: ignore


async def test_store(mock_chromadb_store: ChromaVectorStore) -> None:
    data = [
        VectorStoreEntry(
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
                "__metadata": '{"content": "test content", "document": {"title": "test title", "source":'
                ' {"path": "/test/path"}, "document_type": "test_type"}}',
            }
        ],
        documents=["test_key"],
    )


@pytest.mark.parametrize(
    ("max_distance", "results"),
    [
        (
            None,
            [
                {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]},
                {"content": "test content 2", "title": "test title 2", "vector": [0.13, 0.26, 0.30]},
            ],
        ),
        (0.1, [{"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]}]),
        (0.09, []),
    ],
)
async def test_retrieve(
    mock_chromadb_store: ChromaVectorStore, max_distance: float | None, results: list[dict]
) -> None:
    vector = [0.1, 0.2, 0.3]
    mock_collection = mock_chromadb_store._get_chroma_collection()
    mock_collection.query.return_value = {  # type: ignore
        "metadatas": [
            [
                {
                    "__metadata": '{"content": "test content 1", "document": {"title": "test title 1", "source":'
                    ' {"path": "/test/path-1"}, "document_type": "txt"}}',
                },
                {
                    "__metadata": '{"content": "test content 2", "document": {"title": "test title 2", "source":'
                    ' {"path": "/test/path-2"}, "document_type": "txt"}}',
                },
            ]
        ],
        "embeddings": [[[0.12, 0.25, 0.29], [0.13, 0.26, 0.30]]],
        "distances": [[0.1, 0.2]],
        "documents": [["test_key_1", "test_key_2"]],
        "ids": [["test_id_1", "test_id_2"]],
    }

    entries = await mock_chromadb_store.retrieve(vector, options=VectorStoreOptions(max_distance=max_distance))

    assert len(entries) == len(results)
    for entry, result in zip(entries, results, strict=False):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document"]["title"] == result["title"]
        assert entry.vector == result["vector"]


async def test_list(mock_chromadb_store: ChromaVectorStore) -> None:
    mock_collection = mock_chromadb_store._get_chroma_collection()
    mock_collection.get.return_value = {  # type: ignore
        "metadatas": [
            {
                "__metadata": '{"content": "test content", "document": {"title": "test title", "source":'
                ' {"path": "/test/path"}, "document_type": "test_type"}}',
            },
            {
                "__metadata": '{"content": "test content 2", "document": {"title": "test title 2", "source":'
                ' {"path": "/test/path"}, "document_type": "test_type"}}',
            },
        ],
        "embeddings": [[0.12, 0.25, 0.29], [0.13, 0.26, 0.30]],
        "documents": ["test_key", "test_key_2"],
        "ids": ["test_id_1", "test_id_2"],
    }

    entries = await mock_chromadb_store.list()

    assert len(entries) == 2
    assert entries[0].metadata["content"] == "test content"
    assert entries[0].metadata["document"]["title"] == "test title"
    assert entries[0].vector == [0.12, 0.25, 0.29]
    assert entries[1].metadata["content"] == "test content 2"
    assert entries[1].metadata["document"]["title"] == "test title 2"
    assert entries[1].vector == [0.13, 0.26, 0.30]
