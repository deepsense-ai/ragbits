import typing
from unittest.mock import AsyncMock

import pytest
from qdrant_client.http import models

from ragbits.core.embeddings import EmbeddingType
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


@pytest.fixture
def mock_qdrant_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=AsyncMock(),
        index_name="test_collection",
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
async def test_store_and_retrieve(store: QdrantVectorStore, entry: VectorStoreEntry):
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
async def test_list(store: QdrantVectorStore, entry: VectorStoreEntry):
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
async def test_remove(store: QdrantVectorStore, entry: VectorStoreEntry):
    """Test removing entries."""
    # Store entry
    await store.store([entry])

    # Remove entry
    await store.remove([entry.id])

    # List entries
    entries = await store.list()
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_store(mock_qdrant_store: QdrantVectorStore) -> None:
    data = [
        VectorStoreEntry(
            id="1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
            key="test_key",
            text="test content",
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

    mock_qdrant_store._client.collection_exists.return_value = False  # type: ignore
    await mock_qdrant_store.store(data)

    mock_qdrant_store._client.collection_exists.assert_called_once()  # type: ignore
    mock_qdrant_store._client.create_collection.assert_called_once()  # type: ignore
    mock_qdrant_store._client.upload_collection.assert_called_with(  # type: ignore
        collection_name="test_collection",
        vectors=[[0.1, 0.2, 0.3]],
        payload=[
            {
                "document": "test_key",
                "metadata": '{"content": "test content", '
                '"document": {"title": "test title", "source": {"path": "/test/path"}, "document_type": "test_type"}}',
            }
        ],
        ids=["1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"],
        wait=True,
    )


@pytest.mark.asyncio
async def test_retrieve_mock(mock_qdrant_store: QdrantVectorStore) -> None:
    mock_qdrant_store._client.search.return_value = [  # type: ignore
        models.ScoredPoint(
            version=1,
            id="1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
            vector=[0.12, 0.25, 0.29],
            score=0.9,
            payload={
                "document": "test_key 1",
                "metadata": '{"content": "test content 1",'
                '"document": {"title": "test title 1", '
                '"source": {"path": "/test/path-1"}, "document_type": "txt"}}',
            },
        ),
        models.ScoredPoint(
            version=1,
            id="827cad0b-058f-4b85-b8ed-ac741948d502",
            vector=[0.13, 0.26, 0.30],
            score=0.9,
            payload={
                "document": "test_key 2",
                "metadata": '{"content": "test content 2", '
                '"document": {"title": "test title 2", '
                '"source": {"path": "/test/path-2"}, "document_type": "txt"}}',
            },
        ),
    ]

    query = VectorStoreEntry(
        id="test_id",
        key="test_key",
        text="test query",
        metadata={},
    )
    results = await mock_qdrant_store.retrieve(query)

    assert len(results) == 2
    for result in results:
        assert result.entry.metadata["content"].startswith("test content")
        assert result.entry.metadata["document"]["title"].startswith("test title")
        assert len(result.vectors) == 1
        assert str(EmbeddingType.TEXT) in result.vectors
        assert isinstance(result.score, float)


@pytest.mark.asyncio
async def test_remove_mock_client(mock_qdrant_store: QdrantVectorStore) -> None:
    """Test that remove calls the Qdrant client correctly."""
    ids_to_remove = ["1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"]

    await mock_qdrant_store.remove(ids_to_remove)

    mock_qdrant_store._client.delete.assert_called_once()  # type: ignore
    mock_qdrant_store._client.delete.assert_called_with(  # type: ignore
        collection_name="test_collection",
        points_selector=models.PointIdsList(
            points=typing.cast(list[int | str], ids_to_remove),
        ),
    )


@pytest.mark.asyncio
async def test_list_mock_client(mock_qdrant_store: QdrantVectorStore) -> None:
    """Test that list calls the Qdrant client correctly and processes the response."""
    mock_qdrant_store._client.collection_exists.return_value = True  # type: ignore
    mock_qdrant_store._client.query_points.return_value = models.QueryResponse(  # type: ignore
        points=[
            models.ScoredPoint(
                version=1,
                id="1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                vector=[0.12, 0.25, 0.29],
                score=0.9,
                payload={
                    "document": "test_key 1",
                    "metadata": '{"content": "test content 1",'
                    '"document": {"title": "test title 1", '
                    '"source": {"path": "/test/path-1"}, "document_type": "txt"}}',
                },
            ),
            models.ScoredPoint(
                version=1,
                id="827cad0b-058f-4b85-b8ed-ac741948d502",
                vector=[0.13, 0.26, 0.30],
                score=0.9,
                payload={
                    "document": "test_key 2",
                    "metadata": '{"content": "test content 2", '
                    '"document": {"title": "test title 2", '
                    '"source": {"path": "/test/path-2"}, "document_type": "txt"}}',
                },
            ),
        ]
    )

    entries = await mock_qdrant_store.list()

    assert len(entries) == 2
    for entry in entries:
        assert entry.metadata["content"].startswith("test content")
        assert entry.metadata["document"]["title"].startswith("test title")
        assert entry.key.startswith("test_key")
