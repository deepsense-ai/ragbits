from ragbits.core.metadata_store.in_memory import InMemoryMetadataStore


async def test_in_memory_vector_store():
    store = InMemoryMetadataStore()

    metadata_key_1_values = {"test1": "test1", "test2": 2}
    metadata_key_2_values = {"test1": "test1", "test2": 4}
    await store.store("key1", metadata_key_1_values)
    await store.store("key2", metadata_key_2_values)

    assert await store.get("key1") == metadata_key_1_values
    assert await store.get("key2") == metadata_key_2_values

    assert await store.query("test2", 2) == {"key1": metadata_key_1_values}
    assert await store.query("test1", "test1") == {"key1": metadata_key_1_values, "key2": metadata_key_2_values}


async def test_in_memory_vector_store_global():
    store = InMemoryMetadataStore()

    metadata = {"test1": "test1", "test2": 2}
    await store.store_global(metadata)
    assert await store.get_global() == metadata


async def test_in_memory_vector_store_all():
    store = InMemoryMetadataStore()

    metadata = {"key1": {"test1": "test1", "test2": 2}, "key2": {"test1": "test1", "test2": 2}}
    for k, v in metadata.items():
        await store.store(k, v)
    assert await store.get_all() == metadata
