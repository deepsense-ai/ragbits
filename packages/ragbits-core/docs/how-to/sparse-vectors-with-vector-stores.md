# Using Sparse Vectors with Vector Stores

This guide explains how to use sparse embeddings with vector stores in Ragbits.

## What are Sparse Vectors?

Sparse vectors are embeddings where most elements are zero. They're particularly useful for:

- **Lexical search**: Capturing exact keyword matches
- **Interpretability**: Each dimension often corresponds to a specific term
- **Efficiency**: Only non-zero elements need to be stored

Unlike dense vectors (where all dimensions have values), sparse vectors excel at preserving exact term matches, making them complementary to dense vectors in search applications.

## Using Sparse Embeddings in Ragbits

Ragbits supports sparse embeddings through the `BM25Embedder` class, which implements a popular sparse embedding algorithm.

### Creating a Sparse Embedder

```python
from ragbits.core.embeddings.sparse import BM25Embedder

# Create a BM25 sparse embedder
sparse_embedder = BM25Embedder()
```

### Using Sparse Embeddings with Vector Stores

Ragbits vector stores support sparse embeddings. Here's how to use them:

```python
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.base import EmbeddingType, VectorStoreOptions
import uuid

# Create a vector store with sparse embedder
vector_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT,
    default_options=VectorStoreOptions(k=5)
)

# Create and store entries
from ragbits.core.vector_stores.base import VectorStoreEntry

entries = [
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="Machine learning algorithms can process large datasets",
        metadata={"category": "ML"}
    ),
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="Natural language processing helps computers understand human language",
        metadata={"category": "NLP"}
    )
]

# Store entries
await vector_store.store(entries)

# Retrieve entries using sparse embeddings
results = await vector_store.retrieve("language processing algorithms")

# Process results
for result in results:
    print(f"Text: {result.entry.text}")
    print(f"Score: {result.score}")
    print(f"Metadata: {result.entry.metadata}")
    print("---")
```

## Supported Vector Stores

The following vector stores in Ragbits support sparse embeddings:

- **InMemoryVectorStore**: For in-memory storage and retrieval
- **QdrantVectorStore**: For persistent storage using Qdrant

## When to Use Sparse Embeddings

Sparse embeddings are particularly useful when:

1. **Exact keyword matching is important**: When you need to find documents containing specific terms
2. **Interpretability matters**: When you need to understand why certain results were returned
3. **As part of hybrid search**: Combined with dense embeddings for better overall results

## Combining with Dense Embeddings (Hybrid Search)

For the best results, consider using both sparse and dense embeddings together in a hybrid approach. See the [Hybrid Search guide](hybrid-search.md) for details.

## Performance Considerations

- Sparse vectors can be more memory-efficient for storage but may require specialized indexing
- The BM25 algorithm needs to build a vocabulary from your corpus, which requires an initial processing step
- For very large datasets, consider using a vector database that natively supports sparse vectors

## Next Steps

- Explore [Hybrid Search with Vector Stores](hybrid-search.md) to combine sparse and dense embeddings
- Learn about different embedding models available in Ragbits
