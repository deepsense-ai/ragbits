from unittest.mock import Mock, AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError
from qdrant_client.http import models
from qdrant_client.models import Distance
import weaviate.classes as wvc

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.utils.pydantic import _pydantic_bytes_to_hex
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.weaviate_vector import WeaviateVectorStore


@pytest.fixture
def mock_weaviate_store() -> WeaviateVectorStore:
    client = AsyncMock()
    return WeaviateVectorStore(
        client=client,
        index_name="test_collection",
        embedder=NoopEmbedder(return_values=[[[0.1, 0.2, 0.3]]], image_return_values=[[[0.7, 0.8, 0.9]]]),
    )

async def test_store(mock_weaviate_store: WeaviateVectorStore) -> None:
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
        # VectorStoreEntry(
        #     id=UUID("827cad0b-058f-4b85-b8ed-ac741948d502"),
        #     text="some other key",
        #     image_bytes=b"image",
        #     metadata={
        #         "content": "test content",
        #         "document_meta": {
        #             "title": "test title",
        #             "source": {"path": "/test/path"},
        #             "document_type": "test_type",
        #         },
        #     },
        # ),
    ]

    mock_weaviate_store._client.collections.exists.return_value = False  # type: ignore
    await mock_weaviate_store.store(data)

    mock_weaviate_store._client.collections.exists.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.create.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_called_once()  # type: ignore
    mock_weaviate_store._client.collections.get.assert_called_with("test_collection")

    mock_weaviate_store._client.collections.get.data.insert_many.assert_called_with(  # type: ignore
        [
            wvc.data.DataObject(
                uuid=str(data[0].id),
                properties=data[0].model_dump(exclude={"id"}, exclude_none=True, mode="json"),
                vector=[0.1, 0.2, 0.3]
            )
        ]
    )
