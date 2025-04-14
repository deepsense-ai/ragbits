# How to Use Sparse Embeddings with Vector Stores

This guide explains how to use sparse embeddings with Ragbits vector stores.

## What are Sparse Embeddings?

Sparse embeddings are vector representations where most of the values are zero. They are efficient for representing high-dimensional data where only a few dimensions have non-zero values. In contrast to dense embeddings (which are arrays of floating-point numbers), sparse embeddings store only the indices and values of non-zero elements.

Sparse embeddings are particularly useful for:
- Lexical search (keyword matching)
- Representing large vocabularies efficiently
- Complementing dense embeddings in hybrid search approaches

## Using Sparse Embeddings in Ragbits

Ragbits supports sparse embeddings through the `SparseVector` class and vector stores that can handle both dense and sparse embeddings.

### Step 1: Create a Sparse Embedder

First, you need an embedder that produces sparse vectors:

```python
from ragbits.core.embeddings.sparse import SparseEmbedder, SparseVector

# Example of a simple sparse embedder
sparse_embedder = SparseEmbedder()
```

### Step 2: Initialize a Vector Store with the Sparse Embedder

You can use any of the supported vector stores with sparse embeddings:

```python
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.core.vector_stores.base import EmbeddingType

# Using InMemoryVectorStore with sparse embeddings
vector_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT
)

# Or using QdrantVectorStore with sparse embeddings
from qdrant_client import AsyncQdrantClient
qdrant_client = AsyncQdrantClient(location=":memory:")
qdrant_store = QdrantVectorStore(
    client=qdrant_client,
    index_name="sparse_vectors",
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT
)
```

### Step 3: Store and Retrieve Entries

The process for storing and retrieving entries is the same as with dense embeddings:

```python
import uuid
from ragbits.core.vector_stores.base import VectorStoreEntry

# Create entries
entries = [
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="This is a sample document about artificial intelligence",
        metadata={"category": "AI"}
    ),
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="Sparse vectors are efficient for keyword matching",
        metadata={"category": "NLP"}
    )
]

# Store entries
await vector_store.store(entries)

# Retrieve similar entries
results = await vector_store.retrieve("artificial intelligence")

# Access results
for result in results:
    print(f"Text: {result.entry.text}")
    print(f"Score: {result.score}")
    print(f"Vector type: {type(result.vector).__name__}")
    if isinstance(result.vector, SparseVector):
        print(f"Non-zero elements: {len(result.vector.indices)}")
```

## Performance Considerations

- Sparse vectors are more efficient for storage when the dimensionality is high but most values are zero
- Similarity calculations with sparse vectors can be faster than with dense vectors of the same dimensionality
- For optimal performance with Qdrant, consider using a hybrid approach where both sparse and dense vectors are stored

## Limitations

- Not all vector databases natively support sparse vectors; Ragbits implements workarounds for those cases
- Some advanced vector operations may not be available for sparse vectors
- Performance may vary depending on the specific vector store implementation

## Next Steps

For more advanced use cases, check out the guide on [Hybrid Search with Dense and Sparse Embeddings](hybrid-search.md).
