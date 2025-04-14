# Using Sparse Vectors with Vector Stores

Ragbits supports sparse embeddings through the `SparseVector` and `SparseEmbedder` classes. This guide explains how to use sparse embeddings with vector stores.

## What are Sparse Embeddings?

Unlike dense embeddings (which are represented as arrays of floating-point numbers), sparse embeddings only store non-zero values and their positions. This makes them more efficient for certain types of data and retrieval tasks.

Sparse embeddings are particularly useful for:
- Lexical search (keyword matching)
- Representing large vocabularies efficiently
- Hybrid search approaches combining dense and sparse representations

## Using Sparse Embeddings with Vector Stores

Ragbits vector stores (Qdrant and InMemory) support both dense and sparse embeddings. Here's how to use them:

### 1. Create a Sparse Embedder

First, create a sparse embedder:

```python
from ragbits.core.embeddings.sparse import SparseEmbedder

# Example sparse embedder configuration
sparse_embedder = SparseEmbedder(
    vocabulary_size=10000,
    tokenizer_name="bert-base-uncased"
)
```

### 2. Initialize a Vector Store with the Sparse Embedder

```python
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.core.vector_stores.base import EmbeddingType

# Using InMemoryVectorStore
in_memory_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT
)

# Or using QdrantVectorStore
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance

qdrant_client = AsyncQdrantClient()
qdrant_store = QdrantVectorStore(
    client=qdrant_client,
    index_name="sparse_vectors",
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT,
    distance_method=Distance.COSINE
)
```

### 3. Store and Retrieve Documents

The API for storing and retrieving documents is the same regardless of whether you're using dense or sparse embeddings:

```python
import uuid
from ragbits.core.vector_stores.base import VectorStoreEntry

# Create entries
entries = [
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="This is a sample document for sparse embedding",
        metadata={"source": "example"}
    ),
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="Another document with different keywords",
        metadata={"source": "example"}
    )
]

# Store entries
await vector_store.store(entries)

# Retrieve similar documents
results = await vector_store.retrieve("sample document keywords")

# Process results
for result in results:
    print(f"Score: {result.score}, Text: {result.entry.text}")
    
    # Access the sparse vector if needed
    if hasattr(result.vector, "indices"):
        print(f"Sparse vector with {len(result.vector.indices)} non-zero elements")
```

## Implementation Details

### How Sparse Vectors are Stored

- **InMemoryVectorStore**: Sparse vectors are stored directly in memory as `SparseVector` objects.
- **QdrantVectorStore**: Since Qdrant doesn't natively support sparse vectors, they are stored in the payload of each point with a special key `_sparse_vector`.

### Similarity Calculation

When comparing vectors:
- If both vectors are sparse, dot product is used
- If both vectors are dense, Euclidean distance is used
- If one vector is sparse and the other is dense, the dense vector is converted to a sparse representation before comparison

## Best Practices

1. **Choose the right embedder**: Sparse embedders work best for lexical search, while dense embedders are better for semantic search.
2. **Consider hybrid approaches**: For best results, consider using both sparse and dense embeddings together in a hybrid search approach.
3. **Monitor vector size**: Sparse vectors can be more efficient, but if most values are non-zero, they may be less efficient than dense vectors.
