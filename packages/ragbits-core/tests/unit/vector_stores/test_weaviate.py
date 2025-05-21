from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import weaviate.classes as wvc

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.weaviate_vector import WeaviateVectorStore


@pytest.fixture
def mock_weaviate_client():
    """Create a mock Weaviate client with all necessary components."""
    client = AsyncMock()
    collections = AsyncMock()
    client.collections = collections
    
    # Set up the collection mock
    collection = AsyncMock()
    collections.get.return_value = collection
    collection.data = AsyncMock()
    
    return client


@pytest.fixture
def mock_weaviate_store(mock_weaviate_client):
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


@pytest.mark.asyncio
async def test_store_creates_collection_when_not_exists(mock_weaviate_store, sample_entry):
    """Test that store() creates a new collection when it doesn't exist."""
    # Arrange
    mock_weaviate_store._client.collections.exists.return_value = False
    
    # Act
    await mock_weaviate_store.store([sample_entry])
    
    # Assert
    mock_weaviate_store._client.collections.exists.assert_called_once()
    mock_weaviate_store._client.collections.create.assert_called_once()
    mock_weaviate_store._client.collections.get.assert_called_once_with("test_collection")
    
    expected_object = wvc.data.DataObject(
        uuid=str(sample_entry.id),
        properties=sample_entry.model_dump(exclude={"id"}, exclude_none=True, mode="json"),
        vector=[0.1, 0.2, 0.3]
    )
    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_called_once_with([expected_object])


@pytest.mark.asyncio
async def test_store_uses_existing_collection(mock_weaviate_store, sample_entry):
    """Test that store() uses existing collection when it exists."""
    # Arrange
    mock_weaviate_store._client.collections.exists.return_value = True
    
    # Act
    await mock_weaviate_store.store([sample_entry])
    
    # Assert
    mock_weaviate_store._client.collections.exists.assert_called_once()
    mock_weaviate_store._client.collections.create.assert_not_called()
    mock_weaviate_store._client.collections.get.assert_called_once_with("test_collection")
    
    expected_object = wvc.data.DataObject(
        uuid=str(sample_entry.id),
        properties=sample_entry.model_dump(exclude={"id"}, exclude_none=True, mode="json"),
        vector=[0.1, 0.2, 0.3]
    )
    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_called_once_with([expected_object])


@pytest.mark.asyncio
async def test_store_handles_empty_entries(mock_weaviate_store):
    """Test that store() handles empty entries list correctly."""
    # Act
    await mock_weaviate_store.store([])
    
    # Assert
    mock_weaviate_store._client.collections.exists.assert_not_called()
    mock_weaviate_store._client.collections.create.assert_not_called()
    mock_weaviate_store._client.collections.get.assert_not_called()
    mock_weaviate_store._client.collections.get.return_value.data.insert_many.assert_not_called()
