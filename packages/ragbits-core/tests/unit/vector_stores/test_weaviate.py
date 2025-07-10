from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
import weaviate.classes as wvc
from weaviate.classes.query import Filter
from weaviate.collections.classes.filters import _FilterAnd, _FilterValue
from weaviate.collections.classes.internal import MetadataReturn, Object

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.utils.dict_transformations import flatten_dict
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.weaviate import WeaviateVectorStore, WeaviateVectorStoreOptions


@pytest.fixture
def mock_weaviate_client():
    """Create a mock of Weaviate client with all necessary components."""
    client = AsyncMock()
    collections = AsyncMock()
    client.collections = collections

    # Set up the collection mock
    collection = AsyncMock()
    collections.get = Mock(return_value=collection)
    collection.data = AsyncMock()

    return client


@pytest.fixture
def mock_weaviate_store(mock_weaviate_client: AsyncMock):
    """Create a WeaviateVectorStore instance with a mocked client."""
    return WeaviateVectorStore(
        client=mock_weaviate_client,
        index_name="test_collection",
        embedder=NoopEmbedder(return_values=[[[0.1, 0.2, 0.3]]], image_return_values=[[[0.7, 0.8, 0.9]]]),
    )


@pytest.fixture
def sample_entry():
    """Create a sample vector store entry for testing."""
    return VectorStoreEntry(
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
    )


@pytest.fixture
def sample_entries():
    """Create two sample vector store entries for testing."""
    return [
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


def flatten_metadata(metadata: dict, separator: str = "___") -> dict:
    """Flattens the metadata dictionary."""
    return flatten_dict(metadata, sep=separator)


@pytest.mark.asyncio
async def test_store_adds_multiple_entries(
    mock_weaviate_store: WeaviateVectorStore, sample_entries: list[VectorStoreEntry]
):
    mock_weaviate_store._client.collections.exists.return_value = False  # type: ignore

    await mock_weaviate_store.store(sample_entries)

    mock_weaviate_store._client.collections.exists.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.create.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_called_once_with("test_collection")  # type: ignore

    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_called_once_with(  # type: ignore
        [
            wvc.data.DataObject(
                uuid=str(sample_entries[0].id),
                properties=flatten_metadata(
                    sample_entries[0].model_dump(exclude={"id"}, exclude_none=True, mode="json")
                ),
                vector=[0.1, 0.2, 0.3],
            ),
            wvc.data.DataObject(
                uuid=str(sample_entries[1].id),
                properties=flatten_metadata(
                    sample_entries[1].model_dump(exclude={"id"}, exclude_none=True, mode="json")
                ),
                vector=[0.1, 0.2, 0.3],
            ),
        ]
    )


@pytest.mark.asyncio
async def test_store_creates_collection_when_not_exists(
    mock_weaviate_store: WeaviateVectorStore, sample_entry: VectorStoreEntry
):
    mock_weaviate_store._client.collections.exists.return_value = False  # type: ignore

    await mock_weaviate_store.store([sample_entry])

    mock_weaviate_store._client.collections.exists.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.create.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_called_once_with("test_collection")  # type: ignore

    expected_object = wvc.data.DataObject(
        uuid=str(sample_entry.id),
        properties=flatten_metadata(sample_entry.model_dump(exclude={"id"}, exclude_none=True, mode="json")),
        vector=[0.1, 0.2, 0.3],
    )
    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_called_once_with([expected_object])  # type: ignore


@pytest.mark.asyncio
async def test_store_uses_existing_collection(mock_weaviate_store: WeaviateVectorStore, sample_entry: VectorStoreEntry):
    mock_weaviate_store._client.collections.exists.return_value = True  # type: ignore

    await mock_weaviate_store.store([sample_entry])

    mock_weaviate_store._client.collections.exists.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.create.assert_not_called()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_called_once_with("test_collection")  # type: ignore

    expected_object = wvc.data.DataObject(
        uuid=str(sample_entry.id),
        properties=flatten_metadata(sample_entry.model_dump(exclude={"id"}, exclude_none=True, mode="json")),
        vector=[0.1, 0.2, 0.3],
    )
    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_called_once_with([expected_object])  # type: ignore


async def test_unsupported_type_is_not_added_as_propety(
    mock_weaviate_store: WeaviateVectorStore,
) -> None:
    entry = VectorStoreEntry(
        id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"), text="test", metadata={"unsupported": None}
    )
    mock_weaviate_store._client.collections.exists.return_value = False  # type: ignore
    with pytest.warns(UserWarning, match="Unsupported type of metadata field with key"):
        await mock_weaviate_store.store([entry])

    mock_weaviate_store._client.collections.create.assert_called_once()  # type: ignore
    create_call_kwargs = mock_weaviate_store._client.collections.create.call_args.kwargs  # type: ignore
    assert create_call_kwargs["properties"] == []


async def test_two_entries_with_different_metadata_types(
    mock_weaviate_store: WeaviateVectorStore,
) -> None:
    mock_weaviate_store._client.collections.exists.return_value = False  # type: ignore
    entries = [
        VectorStoreEntry(id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"), text="test", metadata={"unsupported": 1}),
        VectorStoreEntry(id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"), text="test", metadata={"unsupported": "1"}),
    ]

    with pytest.raises(ValueError, match="was already mapped to"):
        await mock_weaviate_store.store(entries)


@pytest.mark.asyncio
async def test_store_handles_empty_entries(mock_weaviate_store: WeaviateVectorStore):
    await mock_weaviate_store.store([])

    mock_weaviate_store._client.collections.exists.assert_not_called()  # type: ignore
    mock_weaviate_store._client.collections.create.assert_not_called()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_not_called()  # type: ignore
    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_not_called()  # type: ignore


@pytest.mark.asyncio
async def test_retrieve(mock_weaviate_store: WeaviateVectorStore):
    mock_weaviate_store._client.collections.get.return_value.query.near_vector.return_value.objects = [  # type: ignore
        Object(
            uuid=UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"),
            metadata=MetadataReturn(
                creation_time=None,
                last_update_time=None,
                distance=0.7,
                certainty=None,
                score=None,
                explain_score=None,
                is_consistent=None,
                rerank_score=None,
            ),
            properties={
                "text": "test_key_1",
                "metadata": {
                    "content": "test content 1",
                    "document_meta": {
                        "document_type": "test_type",
                        "title": "test title 1",
                        "source": {"path": "/test/path"},
                    },
                },
                "image_bytes": None,
            },
            references=None,
            vector={
                "default": [
                    0.12,
                    0.25,
                    0.29,
                ]
            },
            collection="Test_collection",
        ),
        Object(
            uuid=UUID("827cad0b-058f-4b85-b8ed-ac741948d502"),
            metadata=MetadataReturn(
                creation_time=None,
                last_update_time=None,
                distance=0.9,
                certainty=None,
                score=None,
                explain_score=None,
                is_consistent=None,
                rerank_score=None,
            ),
            properties={
                "text": "test_key_2",
                "metadata": {
                    "content": "test content 2",
                    "document_meta": {
                        "title": "test title 2",
                        "document_type": "test_type",
                        "source": {"path": "/test/path"},
                    },
                },
                "image_bytes": b"image",
            },
            references=None,
            vector={
                "default": [
                    0.1,
                    0.2,
                    0.3,
                ]
            },
            collection="Test_collection",
        ),
    ]

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29], "score": -0.7},
        {
            "content": "test content 2",
            "title": "test title 2",
            "vector": [0.1, 0.2, 0.3],
            "score": -0.9,
        },
    ]

    query_results = await mock_weaviate_store.retrieve("query")

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["content"] == result["content"]
        assert query_result.entry.metadata["document_meta"]["title"] == result["title"]
        assert query_result.vector == result["vector"]
        assert query_result.score == result["score"]


@pytest.mark.asyncio
async def test_retrieve_keyword(mock_weaviate_store: WeaviateVectorStore):
    mock_weaviate_store._client.collections.get.return_value.query.bm25.return_value.objects = [  # type: ignore
        Object(
            uuid=UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"),
            metadata=MetadataReturn(
                creation_time=None,
                last_update_time=None,
                distance=None,
                certainty=None,
                score=0.4,
                explain_score=None,
                is_consistent=None,
                rerank_score=None,
            ),
            properties={
                "text": "test_key_1",
                "metadata": {
                    "content": "test content 1",
                    "document_meta": {
                        "document_type": "test_type",
                        "title": "test title 1",
                        "source": {"path": "/test/path"},
                    },
                },
                "image_bytes": None,
            },
            references=None,
            vector={
                "default": [
                    0.12,
                    0.25,
                    0.29,
                ]
            },
            collection="Test_collection",
        ),
        Object(
            uuid=UUID("827cad0b-058f-4b85-b8ed-ac741948d502"),
            metadata=MetadataReturn(
                creation_time=None,
                last_update_time=None,
                distance=None,
                certainty=None,
                score=0.2,
                explain_score=None,
                is_consistent=None,
                rerank_score=None,
            ),
            properties={
                "text": "test_key_2",
                "metadata": {
                    "content": "test content 2",
                    "document_meta": {
                        "title": "test title 2",
                        "document_type": "test_type",
                        "source": {"path": "/test/path"},
                    },
                },
                "image_bytes": b"image",
            },
            references=None,
            vector={
                "default": [
                    0.1,
                    0.2,
                    0.3,
                ]
            },
            collection="Test_collection",
        ),
    ]

    results = [
        {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29], "score": 0.4},
        {
            "content": "test content 2",
            "title": "test title 2",
            "vector": [0.1, 0.2, 0.3],
            "score": 0.2,
        },
    ]

    vector_store_options = WeaviateVectorStoreOptions(k=3, use_keyword_search=True)
    query_results = await mock_weaviate_store.retrieve("query", vector_store_options)

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["content"] == result["content"]
        assert query_result.entry.metadata["document_meta"]["title"] == result["title"]
        assert query_result.vector == result["vector"]
        assert query_result.score == result["score"]


@pytest.mark.asyncio
async def test_remove(mock_weaviate_store: WeaviateVectorStore):
    mock_weaviate_store._client.collections.exists.return_value = True  # type: ignore
    ids_to_remove = [UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8")]

    await mock_weaviate_store.remove(ids_to_remove)

    mock_weaviate_store._client.collections.exists.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_called_once_with("test_collection")  # type: ignore
    mock_weaviate_store._client.collections.get.return_value.data.delete_many.assert_called_once_with(  # type: ignore
        where=Filter.by_id().contains_any(ids_to_remove)
    )


@pytest.mark.asyncio
async def test_list_no_filtering(mock_weaviate_store: WeaviateVectorStore):
    mock_weaviate_store._client.collections.exists.return_value = True  # type: ignore
    mock_weaviate_store._client.collections.get.return_value.aggregate.over_all.return_value.total_count = 2  # type: ignore
    mock_weaviate_store._client.collections.get.return_value.query.fetch_objects.return_value.objects = [  # type: ignore
        Object(
            uuid=UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"),
            metadata=MetadataReturn(
                creation_time=None,
                last_update_time=None,
                distance=None,
                certainty=None,
                score=None,
                explain_score=None,
                is_consistent=None,
                rerank_score=None,
            ),
            properties={
                "text": "test_key_1",
                "metadata": {
                    "content": "test content 1",
                    "document_meta": {
                        "document_type": "test_type",
                        "title": "test title 1",
                        "source": {"path": "/test/path"},
                    },
                },
                "image_bytes": None,
            },
            references=None,
            vector={
                "default": [
                    0.1,
                    0.2,
                    0.3,
                ]
            },
            collection="Test_collection",
        ),
        Object(
            uuid=UUID("827cad0b-058f-4b85-b8ed-ac741948d502"),
            metadata=MetadataReturn(
                creation_time=None,
                last_update_time=None,
                distance=None,
                certainty=None,
                score=None,
                explain_score=None,
                is_consistent=None,
                rerank_score=None,
            ),
            properties={
                "text": "test_key_2",
                "metadata": {
                    "content": "test content 2",
                    "document_meta": {
                        "title": "test title 2",
                        "document_type": "test_type",
                        "source": {"path": "/test/path"},
                    },
                },
                "image_bytes": b"image",
            },
            references=None,
            vector={
                "default": [
                    0.1,
                    0.2,
                    0.3,
                ]
            },
            collection="Test_collection",
        ),
    ]

    results: list[dict] = [
        {"content": "test content 1", "title": "test title 1", "image": None},
        {
            "content": "test content 2",
            "title": "test title 2",
            "image": b"image",
        },
    ]

    entries = await mock_weaviate_store.list()

    assert len(entries) == len(results)
    for i, (entry, result) in enumerate(zip(entries, results, strict=True)):
        assert entry.metadata["content"] == result["content"]
        assert entry.metadata["document_meta"]["title"] == result["title"]
        assert entry.image_bytes == result["image"]
        assert entry.text == f"test_key_{i + 1}"


@pytest.mark.asyncio
async def test_create_weaviate_filter():
    where = {"a": "A", "b": 3, "c": True}
    weaviate_filter = WeaviateVectorStore._create_weaviate_filter(where, separator="___")  # type: ignore
    assert isinstance(weaviate_filter, _FilterAnd)
    assert isinstance(weaviate_filter.filters[0], _FilterValue)
    assert weaviate_filter.filters[0].target == "metadata___a"  # type: ignore
    assert weaviate_filter.filters[0].value == "A"  # type: ignore
    assert weaviate_filter.filters[1].target == "metadata___b"  # type: ignore
    assert weaviate_filter.filters[1].value == 3  # type: ignore
    assert weaviate_filter.filters[2].target == "metadata___c"  # type: ignore
    assert weaviate_filter.filters[2].value  # type: ignore


@pytest.mark.asyncio
async def test_create_weaviate_filter_nested_dict():
    where = {"a": "A", "b": {"c": "d"}}
    weaviate_filter = WeaviateVectorStore._create_weaviate_filter(where, separator="___")  # type: ignore
    assert isinstance(weaviate_filter, _FilterAnd)
    assert weaviate_filter.filters[0].target == "metadata___a"  # type: ignore
    assert weaviate_filter.filters[0].value == "A"  # type: ignore
    assert weaviate_filter.filters[1].target == "metadata___b___c"  # type: ignore
    assert weaviate_filter.filters[1].value == "d"  # type: ignore
