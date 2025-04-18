# How to Perform Hybrid Search with Multiple Vector Stores

Ragbits comes with a special type of vector store called [`HybridSearchVectorStore`][ragbits.core.vector_stores.hybrid.HybridSearchVectorStore], which allows you to combine multiple vector stores into a single search index. It acts as a single vector store but internally manages querying and updating multiple vector stores during operations like storing, searching, and deleting entries.

The main use cases for using a hybrid vector store are:

* **Combining Different Modalities**: You can combine multiple vector stores that store different types of data, like text and images. This allows you to store multiple modality-specific vectors for the same entry (for example, an image embedding and a text embedding of a description of the image) and search them together.
* **Combining Different Types of Embeddings**: You can combine multiple vector stores that store different types of embeddings, like dense and sparse embeddings. This allows you to store multiple embeddings for the same entry and search them simultaneously.

!!! info
    <!-- TODO: Remove this once sparse embedding support in Vector Stores is implemented -->
    Sparse embeddings support in Vector Stores is an upcoming feature of Ragbits. The examples below will be updated to show how to use them with hybrid search once they are available.

## Using a Hybrid Vector Store with Different Modalities

To create a hybrid vector store, you need to pass a list of vector stores to the constructor of the [`HybridSearchVectorStore`][ragbits.core.vector_stores.hybrid.HybridSearchVectorStore] class. For example, this creates two in-memory vector stores—one for text and one for images:

```python
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.embeddings.vertex_multimodal import VertexAIMultimodelEmbedder

embedder = VertexAIMultimodelEmbedder()

vector_store_text = InMemoryVectorStore(embedder=embedder, embedding_type=EmbeddingType.TEXT)
vector_store_image = InMemoryVectorStore(embedder=embedder, embedding_type=EmbeddingType.IMAGE)

vector_store_hybrid = HybridSearchVectorStore(vector_store_text, vector_store_image)
```

You can then use the `vector_store_hybrid` object to store, search, and delete entries, just as you would use a regular vector store, or pass it to [Ragbits' Document Search](../document_search/ingest-documents.md). When you store an entry in the hybrid vector store, it will be stored in all the vector stores it contains. In this case, one will store the text embedding and the other will store the image embedding.

## Using a Hybrid Vector Store with Different Types of Embeddings

<!-- TODO: Change this example to dense and sparse embeddings once sparse embedding support in Vector Stores is implemented -->
Similarly, you can create a hybrid vector store with different types of embeddings. For example, this creates two in-memory vector stores—one using an embedding model from OpenAI and one using an embedding model from Mistral:

```python
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.embeddings.litellm import LiteLLMEmbedder

vector_store_openai = InMemoryVectorStore(embedder=LiteLLMEmbedder(model="text-embedding-ada-002"))
vector_store_mistral = InMemoryVectorStore(embedder=LiteLLMEmbedder(model="mistral/mistral-embed"))

vector_store_hybrid = HybridSearchVectorStore(vector_store_openai, vector_store_mistral)
```

You can then use the `vector_store_hybrid` object to store, search, and delete entries, just as you would use a regular vector store, or pass it to [Ragbits' Document Search](../document_search/ingest-documents.md). When you store an entry in the hybrid vector store, it will be stored in all the vector stores it contains. In this case, one will store the embedding using the OpenAI model and the other will store the embedding using the Mistral model.

Note that you can pass an arbitrary number of vector stores to the `HybridSearchVectorStore` constructor, and they can be of any type as long as they implement the `VectorStore` interface. For example, this combines three vector stores—one Chroma vector store, one Qdrant vector store, and one PgVector vector store:

```python
import asyncpg
from chromadb import EphemeralClient
from qdrant_client import AsyncQdrantClient

from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.core.vector_stores.pgvector import PgVectorStore
from ragbits.core.embeddings.litellm import LiteLLMEmbedder

postgres_pool = await asyncpg.create_pool("postgresql://user:password@localhost/db")

vector_store_hybrid = HybridSearchVectorStore(
    ChromaVectorStore(
        client=EphemeralClient(),
        index_name="chroma_example",
        embedder=LiteLLMEmbedder(),
    ),
    QdrantVectorStore(
        client=AsyncQdrantClient(location=":memory:"),
        index_name="qdrant_example",
        embedder=LiteLLMEmbedder(),
    ),
    PgVectorStore(
        client=pool,
        table_name="postgres_example",
        vector_size=1536,
        embedder=LiteLLMEmbedder(),
    ),
)

# The entry will be stored in all three vector stores
await vector_store_hybrid.store([VectorStoreEntry(id=uuid.uuid4(), text="Example entry")])
```

## Specifying the Retrieval Strategy for a Hybrid Vector Store

When you search a hybrid vector store, you can specify a retrieval strategy to determine how the results from the different vector stores are combined. Ragbits comes with the following retrieval strategies:

* [`OrderedHybridRetrivalStrategy`][ragbits.core.vector_stores.hybrid_strategies.OrderedHybridRetrivalStrategy]: This strategy returns the results from the vector stores ordered by their score. If the same entry is found in multiple vector stores, either the highest score is used or if the `sum_scores` parameter is set to `True`, the scores are summed. This is the default strategy.
* [`ReciprocalRankFusion`][ragbits.core.vector_stores.hybrid_strategies.ReciprocalRankFusion]: This strategy combines the results from the vector stores using the [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) algorithm, which prioritizes entries that appear at the top of the results from individual vector stores. If the same entry is found in multiple vector stores, the scores are summed by default, or if the `sum_scores` parameter is set to `False`, the highest score is used.
* [`DistributionBasedScoreFusion`][ragbits.core.vector_stores.hybrid_strategies.DistributionBasedScoreFusion]: This strategy combines the results from the vector stores using the [Distribution-Based Score Fusion](https://medium.com/plain-simple-software/distribution-based-score-fusion-dbsf-a-new-approach-to-vector-search-ranking-f87c37488b18) algorithm, which normalizes the scores from the individual vector stores so they can be compared and combined sensibly. If the same entry is found in multiple vector stores, either the highest score is used or if the `sum_scores` parameter is set to `True`, the scores are summed.

Note that summing the scores from individual stores boosts the entries found in multiple stores. This can be useful when searching through multiple types of embeddings but may not be desirable when searching through multiple modalities since entries containing both text and image embeddings would have an advantage over those containing only one.

To specify a retrieval strategy when searching a hybrid vector store, you can pass it as the `retrieval_strategy` parameter to the constructor of the [`HybridSearchVectorStore`][ragbits.core.vector_stores.hybrid.HybridSearchVectorStore] class. For example, this creates a hybrid vector store with the `DistributionBasedScoreFusion` retrieval strategy:

```python
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.hybrid_strategies import DistributionBasedScoreFusion
from ragbits.core.embeddings.litellm import LiteLLMEmbedder

embedder = LiteLLMEmbedder()

vector_store_text = InMemoryVectorStore(embedder=embedder, embedding_type=EmbeddingType.TEXT)
vector_store_image = InMemoryVectorStore(embedder=embedder, embedding_type=EmbeddingType.IMAGE)

vector_store_hybrid = HybridSearchVectorStore(
    vector_store_text,
    vector_store_image,
    retrieval_strategy=DistributionBasedScoreFusion(),
)
```
