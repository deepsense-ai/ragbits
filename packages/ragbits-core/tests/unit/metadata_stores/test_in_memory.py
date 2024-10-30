import pytest

from ragbits.core.metadata_stores.exceptions import MetadataNotFoundError
from ragbits.core.metadata_stores.in_memory import InMemoryMetadataStore


@pytest.fixture
def metadata_store() -> InMemoryMetadataStore:
    return InMemoryMetadataStore()


async def test_store(metadata_store: InMemoryMetadataStore) -> None:
    ids = ["id1", "id2"]
    metadatas = [{"key1": "value1"}, {"key2": "value2"}]
    await metadata_store.store(ids, metadatas)
    assert metadata_store._storage["id1"] == {"key1": "value1"}
    assert metadata_store._storage["id2"] == {"key2": "value2"}


async def test_get(metadata_store: InMemoryMetadataStore) -> None:
    ids = ["id1", "id2"]
    metadatas = [{"key1": "value1"}, {"key2": "value2"}]
    await metadata_store.store(ids, metadatas)
    result = await metadata_store.get(ids)
    assert result == [{"key1": "value1"}, {"key2": "value2"}]


async def test_get_metadata_not_found(metadata_store: InMemoryMetadataStore) -> None:
    ids = ["id1"]
    with pytest.raises(MetadataNotFoundError):
        await metadata_store.get(ids)
