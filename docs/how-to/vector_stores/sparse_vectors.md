# How to Use Sparse Vectors with Vector Stores

Sparse embeddings are a representation technique where only non-zero values of a vector are stored along with their indices. This is in contrast to dense embeddings, where all values in the vector are stored regardless of whether they're zero or not. Ragbits supports sparse embeddings through the `SparseVector` and `SparseEmbedder` classes, and now supports using sparse embeddings with vector stores.

## Benefits of Sparse Vectors

Sparse vectors offer several advantages in certain use cases:

1. **Memory efficiency**: By storing only non-zero values, sparse vectors can be much more memory-efficient when the vast majority of values in a vector are zeros.
2. **Interpretability**: Sparse vectors often have better interpretability as each dimension can correspond to a specific token or feature.
3. **Complementary to dense vectors**: When used in hybrid search alongside dense vectors, sparse vectors can improve recall by capturing different aspects of similarity.
4. **Term-weighting**: Sparse vectors can directly represent term frequencies or TF-IDF weights, making them useful for lexical search.

## Supported Vector Stores

Currently, Ragbits supports sparse embeddings with the following vector stores:

- **InMemoryVectorStore**: For quick testing and small-scale use cases
- **QdrantVectorStore**: For production use cases with the Qdrant vector database

## Creating a Sparse Embedder

Ragbits provides several implementations of `SparseEmbedder`:

1. **BagOfTokens**: A simple implementation that creates sparse vectors based on token counts
2. **FastEmbedSparseEmbedder**: Uses the FastEmbed library for efficient sparse embedding generation

Here's an example of creating a sparse embedder using BagOfTokens:

```python
from ragbits.core.embeddings.sparse import BagOfTokens, BagOfTokensOptions

# Create a sparse embedder that uses GPT-4 tokenizer
sparse_embedder = BagOfTokens(
    default_options=BagOfTokensOptions(
        model_name="gpt-4",
        min_token_count=1
    )
)
```

Or using FastEmbedSparseEmbedder:

```python
from ragbits.core.embeddings.fastembed import FastEmbedSparseEmbedder, FastEmbedOptions

# Create a sparse embedder using FastEmbed
sparse_embedder = FastEmbedSparseEmbedder(
    model_name="sentence-transformers/all-MiniLM-L6-v2-sparse",
    use_gpu=True,
    default_options=FastEmbedOptions(batch_size=32)
)
```

## Using Sparse Embeddings with Vector Stores

You can use sparse embeddings with supported vector stores by simply passing a `SparseEmbedder` to the vector store constructor:

### In-Memory Vector Store

```python
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.embeddings.sparse import BagOfTokens, BagOfTokensOptions

# Create a sparse embedder
sparse_embedder = BagOfTokens(
    default_options=BagOfTokensOptions(
        model_name="gpt-4",
        min_token_count=1
    )
)

# Create an in-memory vector store with the sparse embedder
vector_store = InMemoryVectorStore(embedder=sparse_embedder)

# Use the vector store as normal
await vector_store.store([VectorStoreEntry(id=uuid.uuid4(), text="This is a test entry")])
results = await vector_store.retrieve("test query")
```

### Qdrant Vector Store

```python
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.core.embeddings.fastembed import FastEmbedSparseEmbedder, FastEmbedOptions

# Create a sparse embedder
sparse_embedder = FastEmbedSparseEmbedder(
    model_name="sentence-transformers/all-MiniLM-L6-v2-sparse",
    use_gpu=True
)

# Create a Qdrant vector store with the sparse embedder
vector_store = QdrantVectorStore(
    client=AsyncQdrantClient(location=":memory:"),
    index_name="sparse_test",
    embedder=sparse_embedder,
    distance_method=Distance.COSINE
)

# Use the vector store as normal
await vector_store.store([VectorStoreEntry(id=uuid.uuid4(), text="This is a test entry")])
results = await vector_store.retrieve("test query")
```

## Implementation Details

When using sparse embedders with vector stores:

1. The `VectorStoreResult.vector` field may now contain either a `list[float]` (for dense vectors) or a `SparseVector` (for sparse vectors).
2. Vector stores automatically detect whether they're working with dense or sparse vectors based on the type of embedder provided.
3. Similarity calculation is adapted based on vector type:
   - For dense vectors, traditional distance metrics (e.g., cosine similarity, L2 distance) are used
   - For sparse vectors, dot product between the query and document vectors is typically used

## Working with Sparse Vectors Directly

If you need to work with sparse vectors directly, you can use the `SparseVector` class:

```python
from ragbits.core.embeddings.sparse import SparseVector

# Create a sparse vector with non-zero indices and values
vector = SparseVector(
    indices=[1, 5, 10],
    values=[0.5, 0.3, 0.8]
)

# The vector above represents a very large vector where only positions 1, 5, and 10
# have non-zero values (0.5, 0.3, and 0.8 respectively)
``` 