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

=== "Hybrid search"

    ```python
    from ragbits.core.embeddings import LiteLLMEmbedder
    from ragbits.core.vector_stores.qdrant import QdrantVectorStore
    from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
    from ragbits.document_search import DocumentSearch

    embedder = LiteLLMEmbedder(model="text-embedding-3-small", ...)
    vector_store_text = InMemoryVectorStore(embedder=embedder, index_name="text_index", embedding_type=EmbeddingType.TEXT)
    vector_store_image = InMemoryVectorStore(embedder=embedder, index_name="image_index", embedding_type=EmbeddingType.IMAGE)
    vector_store = HybridSearchVectorStore(vector_store_text, vector_store_image)

    document_search = DocumentSearch(vector_store=vector_store, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    Hybrid search is a more advanced strategy that combines multiple vector stores, each optimized for different types of data or embedding models. This approach allows for more flexible and efficient retrieval, as it can leverage the strengths of different vector stores to improve search results. For example, you can combine dense and sparse vector stores or use different embedding models for different data types, or like in this example, use one store for text embeddings and another for image embeddings of the same entry.

    To learn more about using Hybrid Search, refer to [How to Perform Hybrid Search with Multiple Vector Stores](../vector_stores/hybrid.md).

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
    from ragbits.document_search.retrieval.rephrasers import MultiQueryRephraser
    from ragbits.document_search import DocumentSearch

    query_rephraser = MultiQueryRephraser(LiteLLM(model_name="gpt-3.5-turbo"), n=3)
    document_search = DocumentSearch(query_rephraser=query_rephraser, ...)

    elements = await document_search.search("What is the capital of Poland?")
    ```

    Multi query is a bit more sophisticated technique that breaks down the initial query into multiple independent inputs, which are then used separately to query the vector store. Similar to the previous algorithm, this method also utilizes an LLM to generate queries. This type of rephrasing can be particularly useful for multi-hop questions that require multiple rounds of retrieval.

To define a new rephraser, extend the the [`QueryRephraser`][ragbits.document_search.retrieval.rephrasers.base.QueryRephraser] class.

```python
from ragbits.document_search.retrieval.rephrasers import QueryRephraser


class CustomRephraser(QueryRephraser):
    """
    Rephraser that uses a LLM to rephrase queries.
    """

    async def rephrase(self, query: str) -> list[str]:
        """
        Rephrase a query using the LLM.

        Args:
            query: The query to be rephrased.

        Returns:
            List containing the rephrased query.
        """
        responses = await llm.generate(QueryRephraserPrompt(...))
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
