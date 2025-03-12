import uuid
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.utils.pydantic import _pydantic_bytes_to_hex
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore


@pytest.fixture
def mock_chromadb_store() -> ChromaVectorStore:
    return ChromaVectorStore(
        client=MagicMock(),
        index_name="test_index",
        embedder=NoopEmbedder(return_values=[[[0.1, 0.2, 0.3]]], image_return_values=[[[0.7, 0.8, 0.9]]]),
    )


async def test_store(mock_chromadb_store: ChromaVectorStore) -> None:
    data = [
        VectorStoreEntry(
            id=UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"),
            text="test content",
            image_bytes=b"test image",
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

    await mock_chromadb_store.store(data)

    mock_chromadb_store._client.get_or_create_collection().add.assert_called_once()  # type: ignore
    mock_chromadb_store._client.get_or_create_collection().add.assert_called_with(  # type: ignore
        ids=["1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8-text", "1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8-image"],
        embeddings=[[0.1, 0.2, 0.3], [0.7, 0.8, 0.9]],
        metadatas=[
            {
                "content": "test content",
                "document_meta.title": "test title",
                "document_meta.source.path": "/test/path",
                "document_meta.document_type": "test_type",
                "__id": "1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
                "__image": _pydantic_bytes_to_hex(b"test image"),
            }
        ]
        * 2,
        documents=["test content", "test content"],
    )


@pytest.mark.parametrize(
    ("max_distance", "results"),
    [
        (
            None,
            [
                {"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]},
                {
                    "content": "test content 2",
                    "title": "test title 2",
                    "vector": [0.13, 0.26, 0.30],
                    "image": b"test image",
                },
            ],
        ),
        (0.1, [{"content": "test content 1", "title": "test title 1", "vector": [0.12, 0.25, 0.29]}]),
        (0.09, []),
    ],
)
async def test_retrieve(
    mock_chromadb_store: ChromaVectorStore, max_distance: float | None, results: list[dict]
) -> None:
    ids = [str(uuid.uuid5(uuid.NAMESPACE_OID, "test id 1")), str(uuid.uuid5(uuid.NAMESPACE_OID, "test id 2"))]
    mock_chromadb_store._collection.query.return_value = {  # type: ignore
        "metadatas": [
            [
                {
                    "content": "test content 1",
                    "document_meta.title": "test title 1",
                    "document_meta.source.path": "/test/path-1",
                    "document_meta.document_type": "txt",
                    "__id": ids[0],
                },
                {
                    "content": "test content 2",
                    "document_meta.title": "test title 2",
                    "document_meta.source.path": "/test/path-2",
                    "document_meta.document_type": "txt",
                    "__id": ids[1],
                    "__image": _pydantic_bytes_to_hex(b"test image"),
                },
                {
                    "content": "test content 2",
                    "document_meta.title": "test title 2",
                    "document_meta.source.path": "/test/path-2",
                    "document_meta.document_type": "txt",
                    "__id": ids[1],
                    "__image": _pydantic_bytes_to_hex(b"test image"),
                },
            ]
        ],
        "embeddings": [[[0.12, 0.25, 0.29], [0.13, 0.26, 0.30], [0.13, 0.26, 0.90]]],
        "distances": [[0.1, 0.2, 0.5]],
        "documents": [["test content 1", "test content 2", "test content 2"]],
        "ids": [[f"{ids[0]}-text", f"{ids[1]}-text", f"{ids[1]}-image"]],
    }

    query_results = await mock_chromadb_store.retrieve("query", options=VectorStoreOptions(max_distance=max_distance))

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["content"] == result["content"]
        assert query_result.entry.metadata["document_meta"]["title"] == result["title"]
        assert query_result.vector == result["vector"]
        assert query_result.score in [0.1, 0.2]

        assert query_result.entry.id == uuid.uuid5(uuid.NAMESPACE_OID, f"test id {results.index(result) + 1}")
        assert query_result.entry.text == result["content"]
        assert query_result.entry.image_bytes == result.get("image")


async def test_remove(mock_chromadb_store: ChromaVectorStore) -> None:
    ids_to_remove = [UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8")]

    await mock_chromadb_store.remove(ids_to_remove)

    mock_chromadb_store._client.get_or_create_collection().delete.assert_called_once()  # type: ignore
    mock_chromadb_store._client.get_or_create_collection().delete.assert_called_with(  # type: ignore
        ids=[f"{id}-{embedding_type}" for id in ids_to_remove for embedding_type in ["text", "image"]]
    )


async def test_list(mock_chromadb_store: ChromaVectorStore) -> None:
    mock_chromadb_store._collection.get.return_value = {  # type: ignore
        "metadatas": [
            {
                "content": "test content",
                "document_meta.title": "test title",
                "document_meta.source.path": "/test/path",
                "document_meta.document_type": "test_type",
                "__id": "d8184a66-94c2-4bd1-8aeb-7f8a6d4917f0",
            },
            {
                "content": "test content 2",
                "document_meta.title": "test title 2",
                "document_meta.source.path": "/test/path",
                "document_meta.document_type": "test_type",
                "__id": "ee64bd1c-1096-4cca-98fe-78406f8c3ce5",
                "__image": _pydantic_bytes_to_hex(b"test image"),
            },
            {
                "content": "test content 2",
                "document_meta.title": "test title 2",
                "document_meta.source.path": "/test/path",
                "document_meta.document_type": "test_type",
                "__id": "ee64bd1c-1096-4cca-98fe-78406f8c3ce5",
                "__image": _pydantic_bytes_to_hex(b"test image"),
            },
        ],
        "embeddings": [[0.12, 0.25, 0.29], [0.13, 0.26, 0.30], [0.13, 0.26, 0.90]],
        "documents": ["test content 1", "test content 2", "test content 2"],
        "ids": [
            "d8184a66-94c2-4bd1-8aeb-7f8a6d4917f0-text",
            "ee64bd1c-1096-4cca-98fe-78406f8c3ce5-text",
            "ee64bd1c-1096-4cca-98fe-78406f8c3ce5-image",
        ],
    }

    entries = await mock_chromadb_store.list()

    assert len(entries) == 2
    assert entries[0].metadata["content"] == "test content"
    assert entries[0].metadata["document_meta"]["title"] == "test title"
    assert entries[0].text == "test content 1"
    assert entries[0].id == UUID("d8184a66-94c2-4bd1-8aeb-7f8a6d4917f0")
    assert entries[1].metadata["content"] == "test content 2"
    assert entries[1].metadata["document_meta"]["title"] == "test title 2"
    assert entries[1].text == "test content 2"
    assert entries[1].id == UUID("ee64bd1c-1096-4cca-98fe-78406f8c3ce5")


async def test_metadata_roundtrip(mock_chromadb_store: ChromaVectorStore) -> None:
    # Prepare nested metadata structure
    original_metadata = {
        "content": "test content",
        "document_meta": {
            "title": "test title",
            "source": {"path": "/test/path", "type": "pdf"},
            "metadata": {"author": "Test Author", "tags": ["test", "metadata"], "pages": 42},
        },
    }

    # Create and store entry
    input_entry = VectorStoreEntry(
        id=UUID("2aed364b-bd7a-46a7-82a8-38ea9b9dbf2c"),
        text="test content",
        metadata=original_metadata,
    )

    # Mock the collection's behavior for both store and retrieve
    mock_collection = mock_chromadb_store._collection

    # Store the entry
    await mock_chromadb_store.store([input_entry])

    # Verify store called with flattened metadata
    mock_collection.add.assert_called_once()  # type: ignore
    stored_metadata = mock_collection.add.call_args[1]["metadatas"][0]  # type: ignore
    assert stored_metadata["content"] == "test content"
    assert stored_metadata["document_meta.title"] == "test title"
    assert stored_metadata["document_meta.source.path"] == "/test/path"
    assert stored_metadata["document_meta.source.type"] == "pdf"
    assert stored_metadata["document_meta.metadata.author"] == "Test Author"
    assert stored_metadata["document_meta.metadata.pages"] == 42

    # Mock query response with flattened metadata
    mock_collection.query.return_value = {  # type: ignore
        "ids": [["2aed364b-bd7a-46a7-82a8-38ea9b9dbf2c"]],
        "embeddings": [[[0.1, 0.2, 0.3]]],
        "distances": [[0.0]],
        "documents": [["test content"]],
        "metadatas": [[stored_metadata]],
    }

    # Retrieve the entry
    retrieved_entries = await mock_chromadb_store.retrieve("query")
    assert len(retrieved_entries) == 1

    retrieved_metadata = retrieved_entries[0].entry.metadata
    # Verify the nested structure is restored correctly
    assert retrieved_metadata == original_metadata
