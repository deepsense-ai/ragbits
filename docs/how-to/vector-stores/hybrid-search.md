# Hybrid Search with Vector Stores

Hybrid search combines multiple retrieval methods to improve search quality. This guide explains how to implement hybrid search using Ragbits vector stores.

## What is Hybrid Search?

Hybrid search combines different search approaches, typically:
- **Dense retrieval**: Using dense embeddings for semantic similarity
- **Sparse retrieval**: Using sparse embeddings for lexical/keyword matching

By combining these approaches, hybrid search can overcome the limitations of each individual method.

## Implementing Hybrid Search in Ragbits

Ragbits provides a structured approach for combining results from different vector stores:

### 1. Set Up Multiple Vector Stores

First, create vector stores with different embedding types:

```python
from ragbits.core.embeddings.openai import OpenAIEmbedder
from ragbits.core.embeddings.sparse import BM25SparseEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.base import EmbeddingType

# Dense embedder for semantic search (using a specific implementation)
dense_embedder = OpenAIEmbedder(model="text-embedding-3-small")
dense_store = InMemoryVectorStore(
    embedder=dense_embedder,
    embedding_type=EmbeddingType.TEXT
)

# Sparse embedder for lexical search (using a specific implementation)
sparse_embedder = BM25SparseEmbedder()
sparse_store = InMemoryVectorStore(
    embedder=sparse_embedder,
    embedding_type=EmbeddingType.TEXT
)
```

### 2. Use the HybridSearchVectorStore

Ragbits provides a `HybridSearchVectorStore` class that combines multiple vector stores:

```python
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.hybrid_strategies import ReciprocalRankFusion

# Create a hybrid search vector store with a fusion strategy
hybrid_store = HybridSearchVectorStore(
    dense_store, sparse_store,
    strategy=ReciprocalRankFusion()
)
```

Available strategies:
- **OrderedHybridRetrivalStrategy**: Orders results by score and deduplicates them
- **ReciprocalRankFusion**: Combines results based on their ranks rather than raw scores
- **DistributionBasedScoreFusion**: Normalizes scores based on their distribution before combining

### 3. Perform Hybrid Search

```python
# Store your documents in both vector stores
await dense_store.store(entries)
await sparse_store.store(entries)

# Retrieve using the hybrid store
results = await hybrid_store.retrieve("your search query", options=VectorStoreOptions(k=5))

# Process results
for result in results:
    print(f"Score: {result.score}, Text: {result.entry.text}")
```

## Advanced Hybrid Search Techniques

### Custom Fusion Strategies

You can implement custom strategies by extending the `HybridRetrivalStrategy` class:

```python
from ragbits.core.vector_stores.hybrid_strategies import HybridRetrivalStrategy
from ragbits.core.vector_stores.base import VectorStoreResult

class WeightedFusionStrategy(HybridRetrivalStrategy):
    def __init__(self, weights: list[float]):
        """
        Initialize with weights for each result list.

        Args:
            weights: List of weights corresponding to each vector store's results
        """
        self.weights = weights

    def join(self, results: list[list[VectorStoreResult]]) -> list[VectorStoreResult]:
        if len(results) != len(self.weights):
            raise ValueError(f"Expected {len(self.weights)} result lists, got {len(results)}")

        # Create a dictionary to store combined scores
        combined_entries = {}

        # Process results from each store with its corresponding weight
        for result_list, weight in zip(results, self.weights):
            for result in result_list:
                entry_id = result.entry.id
                if entry_id in combined_entries:
                    # Entry already exists, update score
                    combined_entries[entry_id]["score"] += result.score * weight
                    combined_entries[entry_id]["subresults"].append(result)
                else:
                    # New entry
                    combined_entries[entry_id] = {
                        "entry": result.entry,
                        "vector": result.vector,
                        "score": result.score * weight,
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

## Best Practices

1. **Experiment with different strategies**: The best hybrid search strategy depends on your specific use case and data.
2. **Consider query characteristics**: Some queries benefit more from dense retrieval, others from sparse retrieval.
3. **Evaluate with real queries**: Test your hybrid search with real-world queries to ensure it performs well.
4. **Monitor performance**: Keep track of which strategy works best for different types of queries.
5. **Use the same document IDs**: Ensure documents have the same IDs across different vector stores to enable proper fusion.
