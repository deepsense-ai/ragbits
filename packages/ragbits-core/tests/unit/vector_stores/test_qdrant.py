import typing
from unittest.mock import AsyncMock

import pytest
from qdrant_client.http import models
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance

from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


@pytest.fixture
def mock_qdrant_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=AsyncMock(),
        index_name="test_collection",
    )


@pytest.fixture
def vector_store(qdrant_client: AsyncQdrantClient) -> QdrantVectorStore:
    return QdrantVectorStore(client=qdrant_client, index_name="test")


@pytest.fixture
def entries() -> list[VectorStoreEntry]:
    return [
        VectorStoreEntry(
            id="1",
            key="test1",
            text="test1",
            metadata={"embedding_type": "text", "vector": [1.0, 0.0]},
        ),
        VectorStoreEntry(
            id="2",
            key="test2",
            text="test2",
            metadata={"embedding_type": "text", "vector": [0.0, 1.0]},
        ),
    ]


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


async def test_store_and_retrieve(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0])
    assert len(results) == 2
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 1.0  # Cosine similarity
    assert results[1].entry.id == "2"
    assert results[1].entry.key == "test2"
    assert results[1].vectors["text"] == [0.0, 1.0]
    assert results[1].score == 0.0  # Cosine similarity


async def test_store_and_retrieve_with_max_distance(
    vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]
) -> None:
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0], options=vector_store.options_cls(max_distance=0.5))
    assert len(results) == 1
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 1.0  # Cosine similarity


async def test_store_and_retrieve_with_k(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0], options=vector_store.options_cls(k=1))
    assert len(results) == 1
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 1.0  # Cosine similarity


async def test_store_and_list(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list()
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[0].key == "test1"
    assert results[1].id == "2"
    assert results[1].key == "test2"


async def test_store_and_list_with_limit(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list(limit=1)
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].key == "test1"


async def test_store_and_list_with_offset(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list(offset=1)
    assert len(results) == 1
    assert results[0].id == "2"
    assert results[0].key == "test2"


async def test_store_and_list_with_where(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list(where={"embedding_type": "text"})
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[0].key == "test1"
    assert results[1].id == "2"
    assert results[1].key == "test2"


async def test_store_and_remove(vector_store: QdrantVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    await vector_store.remove(["1"])
    results = await vector_store.list()
    assert len(results) == 1
    assert results[0].id == "2"
    assert results[0].key == "test2"


async def test_store_with_different_distance_method(qdrant_client: AsyncQdrantClient) -> None:
    vector_store = QdrantVectorStore(client=qdrant_client, index_name="test", distance_method=Distance.DOT)
    entries = [
        VectorStoreEntry(
            id="1",
            key="test1",
            text="test1",
            metadata={"embedding_type": "text", "vector": [1.0, 0.0]},
        ),
    ]
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0])
    assert len(results) == 1
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 1.0  # Dot product
