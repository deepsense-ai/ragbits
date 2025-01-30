from unittest.mock import MagicMock

import pytest

from ragbits.core.vector_stores.base import EmbeddingType, VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore


@pytest.fixture
def mock_chromadb_store() -> ChromaVectorStore:
    return ChromaVectorStore(
        client=MagicMock(),
        index_name="test_index",
    )


@pytest.fixture
def entry() -> VectorStoreEntry:
    """Create a test entry."""
    return VectorStoreEntry(
        id="test_id",
        key="test_key",
        text="test text",
        metadata={"test_key": "test_value"},
    )


@pytest.mark.asyncio
async def test_store_and_retrieve(store: ChromaVectorStore, entry: VectorStoreEntry):
    """Test storing and retrieving entries."""
    # Store entry
    await store.store([entry])

    # Retrieve entry
    results = await store.retrieve(entry)
    assert len(results) == 1
    result = results[0]
    assert result.entry.id == entry.id
    assert result.entry.key == entry.key
    assert result.entry.metadata == entry.metadata
    assert len(result.vectors) == 1
    assert str(EmbeddingType.TEXT) in result.vectors
    assert isinstance(result.score, float)


@pytest.mark.asyncio
async def test_list(store: ChromaVectorStore, entry: VectorStoreEntry):
    """Test listing entries."""
    # Store entry
    await store.store([entry])

    # List entries
    entries = await store.list()
    assert len(entries) == 1
    assert entries[0].id == entry.id
    assert entries[0].key == entry.key
    assert entries[0].metadata == entry.metadata


@pytest.mark.asyncio
async def test_remove(store: ChromaVectorStore, entry: VectorStoreEntry):
    """Test removing entries."""
    # Store entry
    await store.store([entry])

    # Remove entry
    await store.remove([entry.id])

    # List entries
    entries = await store.list()
    assert len(entries) == 0


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
    mock_chromadb_store._collection.query.return_value = {  # type: ignore
        "metadatas": [
            [
                {
                    "content": "test content 1",
                    "document.title": "test title 1",
                    "document.source.path": "/test/path-1",
                    "document.document_type": "txt",
                },
                {
                    "content": "test content 2",
                    "document.title": "test title 2",
                    "document.source.path": "/test/path-2",
                    "document.document_type": "txt",
                },
            ]
        ],
        "embeddings": [[[0.12, 0.25, 0.29], [0.13, 0.26, 0.30]]],
        "distances": [[0.1, 0.2]],
        "documents": [["test content 1", "test content 2"]],
        "ids": [["test_id_1", "test_id_2"]],
    }

    entries = await mock_chromadb_store.retrieve(vector, options=VectorStoreOptions(max_distance=max_distance))

    assert len(entries) == len(results)
    for entry, result in zip(entries, results, strict=True):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document"]["title"] == result["title"]
        assert entry.vector == result["vector"]
        assert entry.id == f"test_id_{results.index(result) + 1}"
        assert entry.key == result["content"]


async def test_metadata_roundtrip(mock_chromadb_store: ChromaVectorStore) -> None:
    # Prepare nested metadata structure
    original_metadata = {
        "content": "test content",
        "document": {
            "title": "test title",
            "source": {"path": "/test/path", "type": "pdf"},
            "metadata": {"author": "Test Author", "tags": ["test", "metadata"], "pages": 42},
        },
    }

    # Create and store entry
    input_entry = VectorStoreEntry(
        id="test_doc_1", key="test content", vector=[0.1, 0.2, 0.3], metadata=original_metadata
    )

    # Mock the collection's behavior for both store and retrieve
    mock_collection = mock_chromadb_store._collection

    # Store the entry
    await mock_chromadb_store.store([input_entry])

    # Verify store called with flattened metadata
    mock_collection.add.assert_called_once()  # type: ignore
    stored_metadata = mock_collection.add.call_args[1]["metadatas"][0]  # type: ignore
    assert stored_metadata["content"] == "test content"
    assert stored_metadata["document.title"] == "test title"
    assert stored_metadata["document.source.path"] == "/test/path"
    assert stored_metadata["document.source.type"] == "pdf"
    assert stored_metadata["document.metadata.author"] == "Test Author"
    assert stored_metadata["document.metadata.pages"] == 42

    # Mock query response with flattened metadata
    mock_collection.query.return_value = {  # type: ignore
        "ids": [["test_doc_1"]],
        "embeddings": [[[0.1, 0.2, 0.3]]],
        "distances": [[0.0]],
        "documents": [["test content"]],
        "metadatas": [[stored_metadata]],
    }

    # Retrieve the entry
    retrieved_entries = await mock_chromadb_store.retrieve([0.1, 0.2, 0.3])
    assert len(retrieved_entries) == 1

    retrieved_metadata = retrieved_entries[0].metadata
    # Verify the nested structure is restored correctly
    assert retrieved_metadata == original_metadata
