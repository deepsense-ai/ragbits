from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError
from qdrant_client.http import models
from qdrant_client.models import Distance

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.utils.pydantic import _pydantic_bytes_to_hex
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


@pytest.fixture
def mock_qdrant_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=AsyncMock(),
        index_name="test_collection",
        embedder=NoopEmbedder(return_values=[[[0.1, 0.2, 0.3]]], image_return_values=[[[0.7, 0.8, 0.9]]]),
    )


@pytest.fixture
def mock_qdrant_euclid_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=AsyncMock(),
        index_name="test_collection",
        embedder=NoopEmbedder(return_values=[[[0.1, 0.2, 0.3]]], image_return_values=[[[0.7, 0.8, 0.9]]]),
        distance_method=Distance.EUCLID,
    )


async def test_store(mock_qdrant_store: QdrantVectorStore) -> None:
    data = [
        VectorStoreEntry(
            id=UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"),
            text="test_key",
            metadata={
                "content": "test content",
                "document_meta": {
                    "title": "test title",
                    "source": {"path": "/test/path"},
                    "document_type": "test_type",
                },
            },
        ),
        VectorStoreEntry(
            id=UUID("827cad0b-058f-4b85-b8ed-ac741948d502"),
            text="some other key",
            image_bytes=b"image",
            metadata={
                "content": "test content",
                "document_meta": {
                    "title": "test title",
                    "source": {"path": "/test/path"},
                    "document_type": "test_type",
                },
            },
        ),
    ]

    mock_qdrant_store._client.collection_exists.return_value = False  # type: ignore
    await mock_qdrant_store.store(data)

    mock_qdrant_store._client.collection_exists.assert_called_once()  # type: ignore
    mock_qdrant_store._client.create_collection.assert_called_once()  # type: ignore
    mock_qdrant_store._client.upload_points.assert_called_once()  # type: ignore
    call_kwargs = mock_qdrant_store._client.upload_points.call_args.kwargs  # type: ignore
    call_points = list(call_kwargs["points"])

    assert call_kwargs["collection_name"] == "test_collection"
    assert len(call_points) == 2
    assert call_points[0].id == "1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"
    assert call_points[0].vector == {"dense": [0.1, 0.2, 0.3]}
    assert call_points[0].payload == {
        "id": "1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
        "text": "test_key",
        "metadata": {
            "content": "test content",
            "document_meta": {
                "title": "test title",
                "source": {"path": "/test/path"},
                "document_type": "test_type",
            },
        },
    }
    assert call_points[1].id == "827cad0b-058f-4b85-b8ed-ac741948d502"
    assert call_points[1].vector == {"dense": [0.1, 0.2, 0.3]}
    assert call_points[1].payload == {
        "id": "827cad0b-058f-4b85-b8ed-ac741948d502",
        "text": "some other key",
        "metadata": {
            "content": "test content",
            "document_meta": {
                "title": "test title",
                "source": {"path": "/test/path"},
                "document_type": "test_type",
            },
        },
        "image_bytes": _pydantic_bytes_to_hex(b"image"),
    }


async def test_retrieve(mock_qdrant_store: QdrantVectorStore) -> None:
    mock_qdrant_store._client.query_points.return_value = models.QueryResponse(  # type: ignore
        points=[
            models.ScoredPoint(
                version=1,
                id="1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                vector=[0.12, 0.25, 0.29],
                score=0.9,
                payload={
                    "id": "1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                    "text": "test_key 1",
                    "metadata": {
                        "content": "test content 1",
                        "document_meta": {
                            "title": "test title 1",
                            "source": {"path": "/test/path-1"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
            models.ScoredPoint(
                version=1,
                id="827cad0b-058f-4b85-b8ed-ac741948d502",
                vector=[0.7, 0.8, 0.9],
                score=0.7,
                payload={
                    "id": "827cad0b-058f-4b85-b8ed-ac741948d502",
                    "text": "test_key 2",
                    "image_bytes": _pydantic_bytes_to_hex(b"image"),
                    "metadata": {
                        "content": "test content 2",
                        "document_meta": {
                            "title": "test title 2",
                            "source": {"path": "/test/path-2"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
        ]
    )

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29], "score": 0.9},
        {
            "content": "test content 2",
            "title": "test title 2",
            "vector": [0.7, 0.8, 0.9],
            "score": 0.7,
        },
    ]

    query_results = await mock_qdrant_store.retrieve("query")

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["content"] == result["content"]
        assert query_result.entry.metadata["document_meta"]["title"] == result["title"]
        assert query_result.vector == result["vector"]
        assert query_result.score == result["score"]


async def test_retrieve_euclid(mock_qdrant_euclid_store: QdrantVectorStore) -> None:
    mock_qdrant_euclid_store._client.query_points.return_value = models.QueryResponse(  # type: ignore
        points=[
            models.ScoredPoint(
                version=1,
                id="1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                vector=[0.12, 0.25, 0.29],
                score=0.9,
                payload={
                    "id": "1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                    "text": "test_key 1",
                    "metadata": {
                        "content": "test content 1",
                        "document_meta": {
                            "title": "test title 1",
                            "source": {"path": "/test/path-1"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
            models.ScoredPoint(
                version=1,
                id="827cad0b-058f-4b85-b8ed-ac741948d502",
                vector=[0.7, 0.8, 0.9],
                score=0.7,
                payload={
                    "id": "827cad0b-058f-4b85-b8ed-ac741948d502",
                    "text": "test_key 2",
                    "image_bytes": _pydantic_bytes_to_hex(b"image"),
                    "metadata": {
                        "content": "test content 2",
                        "document_meta": {
                            "title": "test title 2",
                            "source": {"path": "/test/path-2"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
        ]
    )

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29], "score": -0.9},
        {
            "content": "test content 2",
            "title": "test title 2",
            "vector": [0.7, 0.8, 0.9],
            "score": -0.7,
        },
    ]

    query_results = await mock_qdrant_euclid_store.retrieve("query")

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["content"] == result["content"]
        assert query_result.entry.metadata["document_meta"]["title"] == result["title"]
        assert query_result.vector == result["vector"]
        assert query_result.score == result["score"]


async def test_remove(mock_qdrant_store: QdrantVectorStore) -> None:
    ids_to_remove = [UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8")]

    await mock_qdrant_store.remove(ids_to_remove)

    mock_qdrant_store._client.delete.assert_called_once()  # type: ignore
    mock_qdrant_store._client.delete.assert_called_with(  # type: ignore
        collection_name="test_collection",
        points_selector=models.PointIdsList(points=["1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"]),
    )


async def test_list(mock_qdrant_store: QdrantVectorStore) -> None:
    mock_qdrant_store._client.collection_exists.return_value = True  # type: ignore
    mock_qdrant_store._client.count.return_value = models.CountResult(count=2)  # type: ignore
    mock_qdrant_store._client.query_points.return_value = models.QueryResponse(  # type: ignore
        points=[
            models.ScoredPoint(
                version=1,
                id="1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                vector=[0.12, 0.25, 0.29],
                score=0.9,
                payload={
                    "id": "1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                    "text": "test_key 1",
                    "metadata": {
                        "content": "test content 1",
                        "document_meta": {
                            "title": "test title 1",
                            "source": {"path": "/test/path-1"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
            models.ScoredPoint(
                version=1,
                id="827cad0b-058f-4b85-b8ed-ac741948d502",
                vector=[0.13, 0.26, 0.30],
                score=0.7,
                payload={
                    "id": "827cad0b-058f-4b85-b8ed-ac741948d502",
                    "text": "test_key 2",
                    "image_bytes": _pydantic_bytes_to_hex(b"image"),
                    "metadata": {
                        "content": "test content 2",
                        "document_meta": {
                            "title": "test title 2",
                            "source": {"path": "/test/path-2"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
        ]
    )

    results: list[dict] = [
        {"content": "test content 1", "title": "test title 1", "image": None},
        {
            "content": "test content 2",
            "title": "test title 2",
            "image": b"image",
        },
    ]

    entries = await mock_qdrant_store.list(where={"document_type": "txt"})

    assert len(entries) == len(results)
    for i, (entry, result) in enumerate(zip(entries, results, strict=True)):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document_meta"]["title"] == result["title"]
        assert entry.image_bytes == result["image"]
        assert entry.text == f"test_key {i + 1}"


def test_create_qdrant_filter() -> None:
    where = {"a": "A", "b": 3, "c": True}
    qdrant_filter = QdrantVectorStore._create_qdrant_filter(where)  # type: ignore
    assert isinstance(qdrant_filter, models.Filter)
    expected_conditions = [
        models.FieldCondition(key="metadata.a", match=models.MatchValue(value="A")),
        models.FieldCondition(key="metadata.b", match=models.MatchValue(value=3)),
        models.FieldCondition(key="metadata.c", match=models.MatchValue(value=True)),
    ]
    assert qdrant_filter.must == expected_conditions


def test_create_qdrant_filter_nested_dict() -> None:
    where = {"a": "A", "b": {"c": "d"}}
    qdrant_filter = QdrantVectorStore._create_qdrant_filter(where)  # type: ignore
    assert isinstance(qdrant_filter, models.Filter)
    expected_conditions = [
        models.FieldCondition(key="metadata.a", match=models.MatchValue(value="A")),
        models.FieldCondition(key="metadata.b.c", match=models.MatchValue(value="d")),
    ]
    assert qdrant_filter.must == expected_conditions


def test_create_qdrant_filter_with_list() -> None:
    where = {"a": "A", "b": ["c", "d"]}
    qdrant_filter = QdrantVectorStore._create_qdrant_filter(where)  # type: ignore
    print(qdrant_filter)
    assert isinstance(qdrant_filter, models.Filter)
    expected_conditions = [
        models.FieldCondition(key="metadata.a", match=models.MatchValue(value="A")),
        models.FieldCondition(key="metadata.b[0]", match=models.MatchValue(value="c")),
        models.FieldCondition(key="metadata.b[1]", match=models.MatchValue(value="d")),
    ]
    assert qdrant_filter.must == expected_conditions


def test_create_qdrant_filter_raises_error() -> None:
    wrong_where_query = {"a": "A", "b": 1.345}
    with pytest.raises(ValidationError):
        QdrantVectorStore._create_qdrant_filter(where=wrong_where_query)  # type: ignore


async def test_retrieve_with_where_clause(mock_qdrant_store: QdrantVectorStore) -> None:
    mock_qdrant_store._client.query_points.return_value = models.QueryResponse(  # type: ignore
        points=[
            models.ScoredPoint(
                version=1,
                id="1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                vector=[0.12, 0.25, 0.29],
                score=0.9,
                payload={
                    "id": "1f908deb-bc9f-4b5a-8b73-2e72d8b44dc5",
                    "text": "test_key 1",
                    "metadata": {
                        "content": "test content 1",
                        "document_meta": {
                            "title": "test title 1",
                            "source": {"path": "/test/path-1"},
                            "document_type": "txt",
                        },
                    },
                },
            ),
        ]
    )

    options = VectorStoreOptions(
        where={
            "document_meta": {
                "document_type": "txt",
                "source": {"path": "/test/path-1"},
            }
        }
    )

    await mock_qdrant_store.retrieve("query", options)

    mock_qdrant_store._client.query_points.assert_called_once()  # type: ignore
    call_kwargs = mock_qdrant_store._client.query_points.call_args.kwargs  # type: ignore

    # Verify that the filter was created correctly
    assert call_kwargs["query_filter"] == models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.document_meta.document_type",
                match=models.MatchValue(value="txt"),
            ),
            models.FieldCondition(
                key="metadata.document_meta.source.path",
                match=models.MatchValue(value="/test/path-1"),
            ),
        ]
    )
