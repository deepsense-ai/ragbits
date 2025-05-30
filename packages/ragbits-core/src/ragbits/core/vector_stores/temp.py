import asyncio
import pickle
from uuid import UUID

import weaviate
from weaviate.classes.config import VectorDistances

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.base import EmbeddingType, VectorStoreEntry
from ragbits.core.vector_stores.weaviate_vector import WeaviateVectorStore

data = [
    VectorStoreEntry(
        id=UUID("1c7d6b27-4ef1-537c-ad7c-676edb8bc8a8"),
        text="Apple pie recipes.",
        metadata={
            "content": "test content 1",
            "document_meta": {
                "title": "test title 1",
                "source": {"path": "/test/path"},
                "document_type": "test_type",
            },
        },
    ),
    VectorStoreEntry(
        id=UUID("827cad0b-058f-4b85-b8ed-ac741948d502"),
        text="New president elections.",
        image_bytes=b"image",
        metadata={
            "content": "test content 2",
            "document_meta": {
                "title": "test title 2",
                "source": {"path": "/test/path"},
                "document_type": "test_type",
            },
        },
    ),
    VectorStoreEntry(
        id=UUID("827cad0b-058f-4b85-b8ed-ac741948d506"),
        text="Metal concert tickets.",
        metadata={
            "content": "test content 3",
            "document_meta": {
                "title": "test title 3",
                "source": {"path": "/test/path"},
                "document_type": "test_type",
            },
        },
    ),
]


async def main():
    client = weaviate.use_async_with_local()
    embedder = NoopEmbedder(return_values=[[[0.1, 0.2, 0.3], [0.9, 0.9, 0.9], [0.12, 0.23, 0.29]]])

    async with client:
        await client.collections.delete("test_collection")

    weaviate_store = WeaviateVectorStore(
        client=client,
        index_name="test_collection",
        embedder=embedder,
        distance_method=VectorDistances.COSINE,  # VectorDistances.L2_SQUARED
        embedding_type=EmbeddingType.TEXT,
    )

    weaviate_store_pickled = pickle.dumps(weaviate_store)
    weaviate_store = pickle.loads(weaviate_store_pickled)

    await weaviate_store.store(data)

    outputs = await weaviate_store.list()
    print(outputs)


if __name__ == "__main__":
    asyncio.run(main())
