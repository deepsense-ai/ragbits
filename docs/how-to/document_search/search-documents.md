# How-To: Search Documents

The Ragbits document search pipeline consists of three sequential steps: query rephrasing, vector search, and reranking. Each step can be parameterized, enabling more sophisticated retrieval.

## Search vectors

Searching for elements is performed using a vector store. [`DocumentSearch`][ragbits.document_search.DocumentSearch] utilizes [`Element`][ragbits.document_search.documents.element.Element] to format entry in the [`VectorStore`][ragbits.core.vector_stores.VectorStore]. The retrieval strategy at this stage depends on the chosen vector store implementation.

=== "Dense search"

    ```python
    from ragbits.core.embeddings import LiteLLMEmbedder
    from ragbits.core.vector_stores.qdrant import QdrantVectorStore
    from ragbits.document_search import DocumentSearch

    embedder = LiteLLMEmbedder(model="text-embedding-3-small", ...)
    vector_store = QdrantVectorStore(embedder=embedder, index_name="index", ...)
    document_search = DocumentSearch(vector_store=vector_store, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    One of the simplest vector search strategies used in Ragbits is dense search. This approach leverages an embedding model to generate vector representations of search queries and compares them against the dense vector representations of ingested elements. It is a straightforward method and often serves as a good starting point for developing a retrieval pipeline.

=== "Sparse search"

    ```python
    from ragbits.core.embeddings.sparse.fastembed import FastEmbedSparseEmbedder
    from ragbits.core.vector_stores.qdrant import QdrantVectorStore
    from ragbits.document_search import DocumentSearch

    # Create a sparse embedder
    sparse_embedder = FastEmbedSparseEmbedder(model_name="prithivida/Splade_PP_en-distil-cocodenser-retriever")

    # Create a vector store with the sparse embedder
    vector_store = QdrantVectorStore(embedder=sparse_embedder, index_name="sparse_index", ...)
    document_search = DocumentSearch(vector_store=vector_store, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    Sparse search uses sparse vector representations where only non-zero values are stored along with their indices. This approach is particularly effective for lexical search, as it can directly represent term frequencies or TF-IDF weights. Sparse vectors often provide better interpretability, as each dimension typically corresponds to a specific token or feature.

    For more details about using sparse vectors with vector stores, see [How to Use Sparse Vectors with Vector Stores](../vector_stores/sparse_vectors.md).

=== "Hybrid search"

    ```python
    from ragbits.core.embeddings.dense import LiteLLMEmbedder
    from ragbits.core.embeddings.sparse.fastembed import FastEmbedSparseEmbedder
    from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
    from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
    from ragbits.document_search import DocumentSearch

    # Create a dense embedder
    dense_embedder = LiteLLMEmbedder(model="text-embedding-3-small", ...)

    # Create a sparse embedder
    sparse_embedder = FastEmbedSparseEmbedder(model_name="prithivida/Splade_PP_en-distil-cocodenser-retriever")

    # Create vector stores with different embedders
    vector_store_dense = InMemoryVectorStore(embedder=dense_embedder)
    vector_store_sparse = InMemoryVectorStore(embedder=sparse_embedder)

    # Combine them into a hybrid vector store
    vector_store = HybridSearchVectorStore(vector_store_dense, vector_store_sparse)
    document_search = DocumentSearch(vector_store=vector_store, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    Hybrid search is a more advanced strategy that combines multiple vector stores, each optimized for different types of data or embedding models. This approach allows for more flexible and efficient retrieval, as it can leverage the strengths of different vector stores to improve search results. The example above shows how to combine dense and sparse embeddings, which can significantly improve search quality by leveraging both semantic similarity (from dense embeddings) and lexical matching (from sparse embeddings).

    To learn more about using Hybrid Search, refer to [How to Perform Hybrid Search with Multiple Vector Stores](../vector_stores/hybrid.md).

## Limit results with metadata-based filtering

You can filter search results based on document metadata using the `where` clause in `VectorStoreOptions`. This allows you to narrow down results to specific document types, sources, or any other metadata fields you've defined.

```python
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.document_search import DocumentSearch, DocumentSearchOptions

# Create vector store options with metadata filtering
vector_store_options = VectorStoreOptions(
    k=2,  # Number of results to return
    score_threshold=0.6,  # Minimum similarity score
    where={"document_meta": {"document_type": "txt"}}  # Filter by document type
)

# Create document search options with the vector store options
options = DocumentSearchOptions(vector_store_options=vector_store_options)

# Search with the filtering options
results = await document_search.search("Your search query", options=options)
```

The `where` clause supports various filtering conditions. For example, you can filter by:
- Document type
- Source
- Custom metadata fields

This filtering happens at the vector store level, making the search more efficient by reducing the number of documents that need to be processed.

## Rephrase query

By default, the input query is provided directly to the embedding model. However, there is an option to add an additional step before vector search. Ragbits offers several common rephrasing techniques that can be utilized to refine the query and generate better embeddings for retrieval.

=== "Paraphrase"

    ```python
    from ragbits.document_search.retrieval.rephrasers import LLMQueryRephraser
    from ragbits.document_search import DocumentSearch

    query_rephraser = LLMQueryRephraser(LiteLLM(model_name="gpt-3.5-turbo"))
    document_search = DocumentSearch(query_rephraser=query_rephraser, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    The simplest form of rephrasing is paraphrasing the input query. This approach utilizes an LLM to expand the query, making it as detailed as possible. This helps generate richer embeddings, ultimately improving the retrieval of relevant elements during the vector search step.

=== "Multi query"

    ```python
    from ragbits.document_search.retrieval.rephrasers import LLMQueryRephraser, LLMQueryRephraserOptions
    from ragbits.document_search import DocumentSearch

    query_rephraser = LLMQueryRephraser(LiteLLM(model_name="gpt-3.5-turbo"), default_options=LLMQueryRephraserOptions(n=3))
    document_search = DocumentSearch(query_rephraser=query_rephraser, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    Multi query is a bit more sophisticated technique that breaks down the initial query into multiple independent inputs, which are then used separately to query the vector store. Similar to the previous algorithm, this method also utilizes an LLM to generate queries. This type of rephrasing can be particularly useful for multi-hop questions that require multiple rounds of retrieval.

To define a new rephraser, extend the the [`QueryRephraser`][ragbits.document_search.retrieval.rephrasers.base.QueryRephraser] class.

```python
from ragbits.document_search.retrieval.rephrasers import QueryRephraser, QueryRephraserOptions


class CustomRephraser(QueryRephraser[QueryRephraserOptions]):
    """
    Rephraser that uses a LLM to rephrase queries.
    """

    options_cls: type[QueryRephraserOptions] = QueryRephraserOptions

    async def rephrase(self, query: str, options: QueryRephraserOptions | None = None) -> Iterable[str]:
        """
        Rephrase a query using the LLM.

        Args:
            query: The query to be rephrased.
            options: The options for rephrasing.

        Returns:
            List containing the rephrased query.
        """
        responses = await llm.generate(CustomRephraserPrompt(...))
        ...
        return [...]
```

## Rerank elements

By default, elements retrieved from the vector store are returned without any post-processing, which may result in irrelevant data. To address this, reranking can be added at the end of the pipeline. Ragbits offers several common reranking algorithms that can be used to reorder and filter search results.

=== "Cross encoder"

    ```python
    from ragbits.document_search.retrieval.rerankers import LiteLLMReranker
    from ragbits.document_search import DocumentSearch

    reranker = LiteLLMReranker(model="cohere/rerank-english-v3.0")
    document_search = DocumentSearch(reranker=reranker, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    The most popular approach is to use cross encoder model. Which is going to compuate scores for each query-element pair and then sort it and apply thresholding. This solution works well, but requires hosting cross encoder model or having access to external provider API that would host one for us.

=== "RRF"

    ```python
    from ragbits.document_search.retrieval.rerankers import ReciprocalRankFusionReranker
    from ragbits.document_search import DocumentSearch

    reranker = ReciprocalRankFusionReranker()
    document_search = DocumentSearch(reranker=reranker, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    If you have entries from multiple retrieval rounds, you may choose to use a simpler algorithm called Reciprocal Rank Fusion (RRF). RRF assigns scores to documents based on their positions in various ranked lists, allowing for the fusion of different ranking sources without the need for tuning.

To define a new reranker, extend the the [`Reranker`][ragbits.document_search.retrieval.rerankers.base.Reranker] class.

```python
from ragbits.document_search.retrieval.rerankers import Reranker, RerankerOptions
from ragbits.document_search.documents.element import Element


class CustomReranker(Reranker[RerankerOptions]):
    """
    Reranker that uses a LLM to rerank elements.
    """

    options_cls: type[RerankerOptions] = RerankerOptions

    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        """
        Rerank elements with LLM.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            options: The options for reranking.

        Returns:
            The reranked elements.
        """
        responses = await llm.generate_with_metadata(ElementsRerankPrompt(...))
        ...
        return [...]
```
