# Hybrid Search with Vector Stores

Hybrid search combines multiple retrieval methods to improve search quality. This guide explains how to implement hybrid search using Ragbits vector stores.

## What is Hybrid Search?

Hybrid search combines different search approaches, typically:
- **Dense retrieval**: Using dense embeddings for semantic similarity
- **Sparse retrieval**: Using sparse embeddings for lexical/keyword matching

By combining these approaches, hybrid search can overcome the limitations of each individual method.

## Implementing Hybrid Search in Ragbits

Ragbits provides several strategies for combining results from different vector stores:

### 1. Set Up Multiple Vector Stores

First, create vector stores with different embedding types:

```python
from ragbits.core.embeddings.dense import DenseEmbedder
from ragbits.core.embeddings.sparse import SparseEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.base import EmbeddingType

# Dense embedder for semantic search
dense_embedder = DenseEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")
dense_store = InMemoryVectorStore(
    embedder=dense_embedder,
    embedding_type=EmbeddingType.TEXT
)

# Sparse embedder for lexical search
sparse_embedder = SparseEmbedder(vocabulary_size=10000)
sparse_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT
)
```

### 2. Choose a Hybrid Retrieval Strategy

Ragbits provides several strategies for combining results:

```python
from ragbits.core.vector_stores.hybrid_strategies import (
    OrderedHybridRetrivalStrategy,
    ReciprocalRankFusion,
    DistributionBasedScoreFusion
)

# Choose one of the available strategies
strategy = ReciprocalRankFusion()
```

Available strategies:
- **OrderedHybridRetrivalStrategy**: Orders results by score and deduplicates them
- **ReciprocalRankFusion**: Combines results based on their ranks rather than raw scores
- **DistributionBasedScoreFusion**: Normalizes scores based on their distribution before combining

### 3. Perform Hybrid Search

```python
async def hybrid_search(query: str, k: int = 5):
    # Get results from both stores
    dense_results = await dense_store.retrieve(query)
    sparse_results = await sparse_store.retrieve(query)

    # Combine results using the chosen strategy
    combined_results = strategy.join([dense_results, sparse_results])

    # Return top k results
    return combined_results[:k]
```

## Advanced Hybrid Search Techniques

### Weighted Combination

You can implement custom weighting between dense and sparse results:

```python
from ragbits.core.vector_stores.hybrid_strategies import HybridRetrivalStrategy
from ragbits.core.vector_stores.base import VectorStoreResult

class WeightedHybridStrategy(HybridRetrivalStrategy):
    def __init__(self, dense_weight: float = 0.7, sparse_weight: float = 0.3):
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:
        if len(results) != 2:
            raise ValueError("WeightedHybridStrategy expects exactly 2 result lists")

        dense_results, sparse_results = results

        # Create a dictionary to store combined scores
        combined_entries = {}

        # Process dense results
        for result in dense_results:
            entry_id = result.entry.id
            combined_entries[entry_id] = {
                "entry": result.entry,
                "vector": result.vector,
                "score": result.score * self.dense_weight,
                "subresults": [result]
            }

        # Process sparse results
        for result in sparse_results:
            entry_id = result.entry.id
            if entry_id in combined_entries:
                # Entry already exists from dense results
                combined_entries[entry_id]["score"] += result.score * self.sparse_weight
                combined_entries[entry_id]["subresults"].append(result)
            else:
                # New entry
                combined_entries[entry_id] = {
                    "entry": result.entry,
                    "vector": result.vector,
                    "score": result.score * self.sparse_weight,
                    "subresults": [result]
                }

        # Convert to VectorStoreResult objects and sort
        combined_results = [
            VectorStoreResult(
                entry=data["entry"],
                vector=data["vector"],
                score=data["score"],
                subresults=data["subresults"]
            )
            for data in combined_entries.values()
        ]

        return sorted(combined_results, key=lambda x: x.score, reverse=True)
```

### Dynamic Weighting

For more advanced scenarios, you can implement dynamic weighting based on query characteristics:

```python
class DynamicWeightedStrategy(HybridRetrivalStrategy):
    def __init__(self, query: str):
        # Analyze query to determine weights
        query_words = query.split()
        if len(query_words) <= 2:
            # Short queries likely benefit more from lexical search
            self.dense_weight = 0.3
            self.sparse_weight = 0.7
        else:
            # Longer queries likely benefit more from semantic search
            self.dense_weight = 0.7
            self.sparse_weight = 0.3

    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:
        # Implementation similar to WeightedHybridStrategy
        # ...
```

## Best Practices

1. **Experiment with different strategies**: The best hybrid search strategy depends on your specific use case and data.
2. **Consider query characteristics**: Some queries benefit more from dense retrieval, others from sparse retrieval.
3. **Evaluate with real queries**: Test your hybrid search with real-world queries to ensure it performs well.
4. **Monitor performance**: Keep track of which strategy works best for different types of queries.
