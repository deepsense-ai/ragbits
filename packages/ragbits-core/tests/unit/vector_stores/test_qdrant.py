import typing
from unittest.mock import AsyncMock

import pytest
from qdrant_client.http import models

from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


@pytest.fixture
def mock_qdrant_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=AsyncMock(),
        index_name="test_collection",
    )


async def test_store(mock_qdrant_store: QdrantVectorStore) -> None:
    data = [
        VectorStoreEntry(
            id="1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
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


async def test_retrieve(mock_qdrant_store: QdrantVectorStore) -> None:
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

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]},
        {"content": "test content 2", "title": "test title 2", "vector": [0.13, 0.26, 0.30]},
    ]

    entries = await mock_qdrant_store.retrieve([0.12, 0.25, 0.29])

    assert len(entries) == len(results)
    for entry, result in zip(entries, results, strict=True):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document"]["title"] == result["title"]
        assert entry.vector == result["vector"]


async def test_remove(mock_qdrant_store: QdrantVectorStore) -> None:
    ids_to_remove = ["1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"]

    await mock_qdrant_store.remove(ids_to_remove)

    mock_qdrant_store._client.delete.assert_called_once()  # type: ignore
    mock_qdrant_store._client.delete.assert_called_with(  # type: ignore
        collection_name="test_collection",
        points_selector=models.PointIdsList(
            points=typing.cast(list[int | str], ids_to_remove),
        ),
    )


async def test_list(mock_qdrant_store: QdrantVectorStore) -> None:
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

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]},
        {"content": "test content 2", "title": "test title 2", "vector": [0.13, 0.26, 0.30]},
    ]

    entries = await mock_qdrant_store.list()

    assert len(entries) == len(results)
    for entry, result in zip(entries, results, strict=True):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document"]["title"] == result["title"]
        assert entry.vector == result["vector"]
