import httpx
from chromadb import ClientAPI
from qdrant_client import AsyncQdrantClient
from qdrant_client.local.async_qdrant_local import AsyncQdrantLocal

from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.core.vector_stores.base import VectorStore, VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore


def test_subclass_from_config():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.vector_stores:InMemoryVectorStore",
            "config": {
                "default_options": {
                    "k": 10,
                    "score_threshold": 0.22,
                },
                "embedder": {
                    "type": "ragbits.core.embeddings:NoopEmbedder",
                },
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, InMemoryVectorStore)
    assert isinstance(store.default_options, VectorStoreOptions)
    assert store.default_options.k == 10
    assert store.default_options.score_threshold == 0.22


def test_subclass_from_config_default_path():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "InMemoryVectorStore",
            "config": {
                "embedder": {"type": "NoopEmbedder"},
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, InMemoryVectorStore)


def test_subclass_from_config_chroma_client():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.vector_stores.chroma:ChromaVectorStore",
            "config": {
                "client": {"type": "EphemeralClient"},
                "index_name": "some_index",
                "default_options": {
                    "k": 10,
                    "score_threshold": 0.22,
                },
                "embedder": {"type": "NoopEmbedder"},
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, ChromaVectorStore)
    assert store._index_name == "some_index"
    assert isinstance(store._client, ClientAPI)
    assert store.default_options.k == 10
    assert store.default_options.score_threshold == 0.22


def test_subclass_from_config_qdrant_client():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.vector_stores.qdrant:QdrantVectorStore",
            "config": {
                "client": {
                    "type": "AsyncQdrantClient",
                    "config": {
                        "location": ":memory:",
                        "limits": {"keepalive_expiry": 20, "max_keepalive_connections": 0},
                    },
                },
                "index_name": "some_index",
                "default_options": {
                    "k": 10,
                    "score_threshold": 0.22,
                },
                "embedder": {"type": "NoopEmbedder"},
            },
        }
    )
    store = VectorStore.subclass_from_config(config)  # type: ignore
    assert isinstance(store, QdrantVectorStore)
    assert store._index_name == "some_index"
    assert isinstance(store._client, AsyncQdrantClient)
    assert isinstance(store._client.init_options["limits"], httpx.Limits)
    assert store._client.init_options["limits"].keepalive_expiry == 20
    assert store._client.init_options["limits"].max_keepalive_connections == 0
    assert isinstance(store._client._client, AsyncQdrantLocal)
    assert store.default_options.k == 10
    assert store.default_options.score_threshold == 0.22
