# How to Implement Hybrid Search with Dense and Sparse Embeddings

This guide explains how to implement hybrid search combining both dense and sparse embeddings in Ragbits.

## What is Hybrid Search?

Hybrid search combines multiple search approaches to get the best of both worlds:

- **Dense embeddings**: Good at capturing semantic meaning and contextual relationships
- **Sparse embeddings**: Excel at lexical matching and keyword preservation

By combining these approaches, you can create more robust search systems that handle both semantic similarity and exact keyword matching.

## Implementing Hybrid Search in Ragbits

Ragbits supports hybrid search through the `HybridSearchVectorStore` class, which can combine results from multiple vector stores.

### Step 1: Create Dense and Sparse Embedders

First, set up both dense and sparse embedders:

```python
from ragbits.core.embeddings.base import Embedder
from ragbits.core.embeddings.sparse import SparseEmbedder

# Dense embedder (example using a pre-configured embedder)
dense_embedder = Embedder.from_config({
    "type": "ragbits.core.embeddings.openai.OpenAIEmbedder",
    "config": {
        "api_key": "your-api-key",
        "model": "text-embedding-ada-002"
    }
})

# Sparse embedder
sparse_embedder = SparseEmbedder()
```

### Step 2: Create Vector Stores for Each Embedder Type

Create separate vector stores for dense and sparse embeddings:

```python
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.base import EmbeddingType, VectorStoreOptions

# Vector store for dense embeddings
dense_store = InMemoryVectorStore(
    embedder=dense_embedder,
    embedding_type=EmbeddingType.TEXT,
    default_options=VectorStoreOptions(k=10)
)

# Vector store for sparse embeddings
sparse_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT,
    default_options=VectorStoreOptions(k=10)
)
```

### Step 3: Create a Hybrid Search Vector Store

Combine the vector stores using `HybridSearchVectorStore`:

```python
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore

hybrid_store = HybridSearchVectorStore(
    stores=[dense_store, sparse_store],
    weights=[0.7, 0.3]  # Weights for each store (must sum to 1.0)
)
```

### Step 4: Store and Retrieve Entries

Store your entries in both vector stores and then query using the hybrid store:

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
        text="Machine learning algorithms can process large datasets",
        metadata={"category": "ML"}
    )
]

# Store entries in both vector stores
await dense_store.store(entries)
await sparse_store.store(entries)

# Retrieve similar entries using hybrid search
results = await hybrid_store.retrieve("AI algorithms for big data")

# Access results
for result in results:
    print(f"Text: {result.entry.text}")
    print(f"Score: {result.score}")
    print(f"Vector type: {type(result.vector).__name__}")
```

## Fine-tuning Hybrid Search

You can adjust the weights of each vector store to optimize for your specific use case:

- Higher weight for dense store: Better semantic understanding but might miss exact keyword matches
- Higher weight for sparse store: Better keyword matching but might miss semantically related content
- Equal weights: Balanced approach

Experiment with different weights to find the optimal configuration for your data and queries.

## Advanced Hybrid Search Techniques

### Reranking

For more sophisticated hybrid search, you can implement a reranking step:

```python
from ragbits.core.vector_stores.base import VectorStoreResult

async def rerank_results(query: str, results: list[VectorStoreResult]) -> list[VectorStoreResult]:
    # Custom reranking logic
    # This could involve additional scoring, filtering, or combining scores in a more complex way
    return sorted(results, key=lambda r: r.score, reverse=True)

# Use in your search pipeline
raw_results = await hybrid_store.retrieve("your query")
final_results = await rerank_results("your query", raw_results)
```

### Query Expansion

You can also implement query expansion to improve search results:

```python
async def expand_query(query: str) -> list[str]:
    # Generate variations of the query
    return [query, f"about {query}", f"{query} explanation"]

expanded_queries = await expand_query("artificial intelligence")
all_results = []

for expanded_query in expanded_queries:
    results = await hybrid_store.retrieve(expanded_query)
    all_results.extend(results)

# Deduplicate and rerank
# ...
```

## Performance Considerations

- Hybrid search requires multiple embedding operations and searches, which can increase latency
- Consider caching embeddings for frequently used queries
- For large-scale applications, you might need to optimize the vector stores for performance

## Next Steps

- Explore [Sparse Vectors with Vector Stores](sparse-vectors-with-vector-stores.md) for more details on sparse embeddings
- Learn about [Vector Store Configuration](vector-store-configuration.md) to optimize your vector stores
