# How to Implement Hybrid Search with Dense and Sparse Embeddings

This guide explains how to implement hybrid search combining both dense and sparse embeddings in Ragbits.

## What is Hybrid Search?

Hybrid search combines multiple search approaches to get the best of both worlds:

- **Dense embeddings**: Good at capturing semantic meaning and contextual relationships
- **Sparse embeddings**: Excel at lexical matching and keyword preservation

By combining these approaches, you can create more robust search systems that handle both semantic similarity and exact keyword matching.

## Implementing Hybrid Search in Ragbits

Ragbits supports hybrid search through the `HybridVectorStore` class, which can combine results from multiple vector stores using different fusion strategies.

### Step 1: Create Dense and Sparse Embedders

First, set up both dense and sparse embedders:

```python
from ragbits.core.embeddings.base import Embedder
from ragbits.core.embeddings.sparse import BM25Embedder

# Dense embedder (example using a pre-configured embedder)
dense_embedder = Embedder.from_config({
    "type": "ragbits.core.embeddings.litellm.LiteLLMEmbedder",
    "config": {
        "model": "text-embedding-ada-002"
    }
})

# Sparse embedder
sparse_embedder = BM25Embedder()
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

### Step 3: Create a Hybrid Vector Store

Combine the vector stores using `HybridVectorStore` with a fusion strategy:

```python
from ragbits.core.vector_stores.hybrid import HybridVectorStore
from ragbits.core.vector_stores.hybrid_strategies import ReciprocalRankFusion

# Using Reciprocal Rank Fusion strategy
hybrid_store = HybridVectorStore(
    vector_stores=[dense_store, sparse_store],
    strategy=ReciprocalRankFusion()
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

    # If you want to see the individual scores from each vector store
    if result.subresults:
        for i, subresult in enumerate(result.subresults):
            store_type = "Dense" if i == 0 else "Sparse"
            print(f"  - {store_type} score: {subresult.score}")
```

## Fusion Strategies

Ragbits provides several strategies for combining results:

1. **OrderedHybridRetrivalStrategy**: Orders results by score and deduplicates them by choosing the first occurrence. This is also known as "Relative Score Fusion".

2. **ReciprocalRankFusion**: Combines results based on their ranks rather than raw scores. This strategy is often more robust to differences in scoring scales between different vector stores.

3. **DistributionBasedScoreFusion**: Normalizes scores based on their distribution before combining them, which can help when different vector stores have very different score distributions.

Choose the strategy that works best for your specific use case.

## Fine-tuning Hybrid Search

You can experiment with different fusion strategies to optimize for your specific use case:

- **OrderedHybridRetrivalStrategy**: Simple and effective when scores are comparable
- **ReciprocalRankFusion**: More robust when scores have different scales
- **DistributionBasedScoreFusion**: Best when score distributions vary significantly

## Advanced Hybrid Search Techniques

### Custom Reranking

For more sophisticated hybrid search, you can implement a custom reranking step:

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

## Performance Considerations

- Hybrid search requires multiple embedding operations and searches, which can increase latency
- Consider caching embeddings for frequently used queries
- For large-scale applications, you might need to optimize the vector stores for performance

## Next Steps

- Explore [Sparse Vectors with Vector Stores](sparse-vectors-with-vector-stores.md) for more details on sparse embeddings
- Learn about the different [Hybrid Retrieval Strategies](https://github.com/deepsense-ai/ragbits/blob/main/packages/ragbits-core/src/ragbits/core/vector_stores/hybrid_strategies.py) available in Ragbits
