import typing
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from qdrant_client.http import models

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


@pytest.fixture
def mock_qdrant_store() -> QdrantVectorStore:
    return QdrantVectorStore(client=AsyncMock(), index_name="test_collection", embedder=NoopEmbedder())


async def test_store(mock_qdrant_store: QdrantVectorStore) -> None:
    data = [
        VectorStoreEntry(
            id="1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
            text="test_key",
            metadata={
                "content": "test content",
                "document_meta": {
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
                "document_meta": {
                    "title": "test title",
                    "source": {"path": "/test/path"},
                    "document_type": "test_type",
                },
                "content": "test content",
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
                    "content": "test content 1",
                    "document_meta": {
                        "title": "test title 1",
                        "source": {"path": "/test/path-1"},
                        "document_type": "txt",
                    },
                },
            ),
            models.ScoredPoint(
                version=1,
                id="827cad0b-058f-4b85-b8ed-ac741948d502",
                vector=[0.13, 0.26, 0.30],
                score=0.9,
                payload={
                    "document": "test_key 2",
                    "content": "test content 2",
                    "document_meta": {
                        "title": "test title 2",
                        "source": {"path": "/test/path-2"},
                        "document_type": "txt",
                    },
                },
            ),
        ]
    )

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]},
        {"content": "test content 2", "title": "test title 2", "vector": [0.13, 0.26, 0.30]},
    ]

    query_results = await mock_qdrant_store.retrieve("query")

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["content"] == result["content"]
        assert query_result.entry.metadata["document_meta"]["title"] == result["title"]
        assert query_result.vectors["text"] == result["vector"]


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
                    "content": "test content 1",
                    "document_meta": {
                        "title": "test title 1",
                        "source": {"path": "/test/path-1"},
                        "document_type": "txt",
                    },
                },
            ),
            models.ScoredPoint(
                version=1,
                id="827cad0b-058f-4b85-b8ed-ac741948d502",
                vector=[0.13, 0.26, 0.30],
                score=0.9,
                payload={
                    "document": "test_key 2",
                    "content": "test content 2",
                    "document_meta": {
                        "title": "test title 2",
                        "source": {"path": "/test/path-2"},
                        "document_type": "txt",
                    },
                },
            ),
        ]
    )

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]},
        {"content": "test content 2", "title": "test title 2", "vector": [0.13, 0.26, 0.30]},
    ]

    entries = await mock_qdrant_store.list(where={"document_type": "txt"})

    assert len(entries) == len(results)
    for entry, result in zip(entries, results, strict=True):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document_meta"]["title"] == result["title"]


def test_create_qdrant_filter() -> None:
    where = {"a": "A", "b": 3, "c": True}
    qdrant_filter = QdrantVectorStore._create_qdrant_filter(where)  # type: ignore
    assert isinstance(qdrant_filter, models.Filter)
    expected_conditions = [
        models.FieldCondition(key="a", match=models.MatchValue(value="A")),
        models.FieldCondition(key="b", match=models.MatchValue(value=3)),
        models.FieldCondition(key="c", match=models.MatchValue(value=True)),
    ]
    assert qdrant_filter.must == expected_conditions


def test_create_qdrant_filter_nested_dict() -> None:
    where = {"a": "A", "b": {"c": "d"}}
    qdrant_filter = QdrantVectorStore._create_qdrant_filter(where)  # type: ignore
    assert isinstance(qdrant_filter, models.Filter)
    expected_conditions = [
        models.FieldCondition(key="a", match=models.MatchValue(value="A")),
        models.FieldCondition(key="b.c", match=models.MatchValue(value="d")),
    ]
    assert qdrant_filter.must == expected_conditions


def test_create_qdrant_filter_with_list() -> None:
    where = {"a": "A", "b": ["c", "d"]}
    qdrant_filter = QdrantVectorStore._create_qdrant_filter(where)  # type: ignore
    print(qdrant_filter)
    assert isinstance(qdrant_filter, models.Filter)
    expected_conditions = [
        models.FieldCondition(key="a", match=models.MatchValue(value="A")),
        models.FieldCondition(key="b[0]", match=models.MatchValue(value="c")),
        models.FieldCondition(key="b[1]", match=models.MatchValue(value="d")),
    ]
    assert qdrant_filter.must == expected_conditions


def test_create_qdrant_filter_raises_error() -> None:
    wrong_where_query = {"a": "A", "b": 1.345}
    with pytest.raises(ValidationError):
        QdrantVectorStore._create_qdrant_filter(where=wrong_where_query)  # type: ignore
