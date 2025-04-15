# How to Use Sparse Vectors with Vector Stores

This guide explains how to use sparse embeddings with vector stores in Ragbits.

## What are Sparse Embeddings?

Sparse embeddings are vector representations where most elements are zero. Unlike dense embeddings (which have values in all dimensions), sparse embeddings:

- Explicitly represent the presence of specific tokens/words
- Excel at lexical matching and keyword preservation
- Are typically high-dimensional but efficient to store due to sparsity

Common sparse embedding techniques include BM25, TF-IDF, and SPLADE.

## Sparse Embeddings in Ragbits

Ragbits provides built-in support for sparse embeddings through the `SparseVector` class and embedders like `BM25Embedder`.

### Creating a Sparse Embedder

```python
from ragbits.core.embeddings.sparse import BM25Embedder

# Create a BM25 sparse embedder
sparse_embedder = BM25Embedder()

# Generate sparse embeddings for a text
text = "This is a sample document about artificial intelligence"
sparse_vector = await sparse_embedder.embed_text(text)

# The result is a SparseVector object
print(f"Indices: {sparse_vector.indices}")
print(f"Values: {sparse_vector.values}")
```

## Using Sparse Embeddings with Vector Stores

Ragbits vector stores support sparse embeddings, allowing you to store and retrieve documents using sparse representations.

### In-Memory Vector Store with Sparse Embeddings

```python
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.base import EmbeddingType, VectorStoreOptions, VectorStoreEntry
import uuid

# Create an in-memory vector store with a sparse embedder
vector_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT,
    default_options=VectorStoreOptions(k=10)
)

# Create entries
entries = [
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="This is a sample document about artificial intelligence",
        metadata={"category": "AI"}
    ),
    VectorStoreEntry(
        id=uuid.uuid4(),
        text="Machine learning algorithms can process large datasets",
        metadata={"category": "ML"}
    )
]

# Store entries
await vector_store.store(entries)

# Retrieve similar entries
results = await vector_store.retrieve("AI algorithms")

# Access results
for result in results:
    print(f"Text: {result.entry.text}")
    print(f"Score: {result.score}")
```

### Qdrant Vector Store with Sparse Embeddings

Qdrant also supports sparse vectors:

```python
from ragbits.core.vector_stores.qdrant import QdrantVectorStore

# Create a Qdrant vector store with a sparse embedder
qdrant_store = QdrantVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT,
    default_options=VectorStoreOptions(k=10),
    collection_name="sparse_docs",
    url="http://localhost:6333"
)

# Store and retrieve entries as with the in-memory store
await qdrant_store.store(entries)
results = await qdrant_store.retrieve("AI algorithms")
```

## Advantages of Sparse Vectors in Search

Sparse vectors offer several advantages for certain search scenarios:

1. **Exact Keyword Matching**: Sparse vectors excel at finding documents containing specific query terms
2. **Interpretability**: The non-zero dimensions in sparse vectors often correspond to specific words
3. **Out-of-Vocabulary Handling**: Sparse vectors can handle terms not seen during training

## When to Use Sparse vs. Dense Embeddings

- **Use sparse embeddings when**:
  - Exact keyword matching is important
  - You need high interpretability
  - The domain contains specialized terminology

- **Use dense embeddings when**:
  - Semantic understanding is more important than exact matches
  - You need to capture contextual relationships
  - The query might use different words than the documents

- **Use hybrid search when**:
  - You want the benefits of both approaches
  - Your use case requires both semantic and lexical matching

## Performance Considerations

- Sparse vectors are typically high-dimensional but storage-efficient due to sparsity
- Some vector stores optimize sparse vector storage and retrieval
- Consider the trade-offs between search quality and performance for your specific use case

## Next Steps

- Explore [Hybrid Search with Dense and Sparse Embeddings](hybrid-search.md) to combine both approaches
- Learn about different sparse embedding techniques beyond BM25
