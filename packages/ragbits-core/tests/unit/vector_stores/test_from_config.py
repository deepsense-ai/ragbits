from chromadb import ClientAPI
from qdrant_client import AsyncQdrantClient
from qdrant_client.local.async_qdrant_local import AsyncQdrantLocal

from ragbits.core.metadata_stores.in_memory import InMemoryMetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.core.vector_stores.base import VectorStore, VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.vector_stores:InMemoryVectorStore",
            "config": {
                "metadata_store": {
                    "type": "ragbits.core.metadata_stores:InMemoryMetadataStore",
                },
                "default_options": {
                    "k": 10,
                    "max_distance": 0.22,
                },
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, InMemoryVectorStore)
    assert isinstance(store.default_options, VectorStoreOptions)
    assert store.default_options.k == 10
    assert store.default_options.max_distance == 0.22
    assert isinstance(store._metadata_store, InMemoryMetadataStore)


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "InMemoryVectorStore"})
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, InMemoryVectorStore)


def test_subclass_from_config_chroma_client():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.vector_stores.chroma:ChromaVectorStore",
            "config": {
                "client": {"type": "EphemeralClient"},
                "index_name": "some_index",
                "default_options": {
                    "k": 10,
                    "max_distance": 0.22,
                },
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, ChromaVectorStore)
    assert store._index_name == "some_index"
    assert isinstance(store._client, ClientAPI)
    assert store.default_options.k == 10
    assert store.default_options.max_distance == 0.22


def test_subclass_from_config_drant_client():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.vector_stores.qdrant:QdrantVectorStore",
            "config": {
                "client": {
                    "type": "AsyncQdrantClient",
                    "config": {
                        "location": ":memory:",
                    },
                },
                "index_name": "some_index",
                "default_options": {
                    "k": 10,
                    "max_distance": 0.22,
                },
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, QdrantVectorStore)
    assert store._index_name == "some_index"
    assert isinstance(store._client, AsyncQdrantClient)
    assert isinstance(store._client._client, AsyncQdrantLocal)
    assert store.default_options.k == 10
    assert store.default_options.max_distance == 0.22
