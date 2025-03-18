# How to Ingest Documents Asynchronously

In Ragbits, a component called "processing execution strategy" controls how document processing is executed during ingestion. There are multiple execution strategies available in Ragbits that can be easily interchanged. You can also [create new custom execution strategies](create_custom_execution_strategy.md) to meet your specific needs.

!!! note
    It's important to note that processing execution strategies are a separate concept from processors. While the former manage how the processing is executed, the latter deals with the actual processing of documents. Processors are managed by [DocumentParserRouter][ragbits.document_search.ingestion.parsers.router.DocumentParserRouter].

## The Synchronous Execution Strategy

The default execution strategy in Ragbits is [`SequentialIngestStrategy`][ragbits.document_search.ingestion.strategies.SequentialIngestStrategy]. This strategy processes documents one by one, waiting for each document to be processed before moving on to the next. Although it's the simplest and most straightforward strategy, it may be slow when processing a large number of documents.

Unless you specify a different strategy, Ragbits will use the [`SequentialIngestStrategy`][ragbits.document_search.ingestion.strategies.SequentialIngestStrategy] strategy by default when ingesting documents:

```python
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

documents = [
    DocumentMeta.create_text_document_from_literal("Example document 1"),
    DocumentMeta.create_text_document_from_literal("Example document 2"),
]

embedder = LiteLLMEmbedder(
    model="text-embedding-3-small",
)
vector_store = InMemoryVectorStore(embedder=embedder)

document_search = DocumentSearch(
    vector_store=vector_store,
)

await document_search.ingest(documents)
```

## The Asynchronous Execution Strategy

If you need to process documents simultaneously, you can use the [`BatchedIngestStrategy`][ragbits.document_search.ingestion.strategies.BatchedIngestStrategy] execution strategy. This strategy uses Python's built-in `asyncio` library to process documents in parallel, making it faster than the [`SequentialIngestStrategy`][ragbits.document_search.ingestion.strategies.SequentialIngestStrategy] strategy, especially with large document volumes.

To use the [`BatchedIngestStrategy`][ragbits.document_search.ingestion.strategies.BatchedIngestStrategy] strategy, specify it when creating the [`DocumentSearch`][ragbits.document_search.DocumentSearch] instance:

```python
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.ingestion.strategies import BatchedIngestStrategy

documents = [
    DocumentMeta.create_text_document_from_literal("Example document 1"),
    DocumentMeta.create_text_document_from_literal("Example document 2"),
]

embedder = LiteLLMEmbedder(
    model="text-embedding-3-small",
)
vector_store = InMemoryVectorStore(embedder=embedder)
ingest_strategy = BatchedIngestStrategy()

document_search = DocumentSearch(
    vector_store=vector_store,
    ingest_strategy=ingest_strategy
)
```

Also, you can adjust the batch size for the [`BatchedIngestStrategy`][ragbits.document_search.ingestion.strategies.BatchedIngestStrategy] strategy. The batch size controls how many documents are processed at once. By default, the batch size is 10, but you can modify it by passing the `batch_size` parameter to the [`BatchedIngestStrategy`][ragbits.document_search.ingestion.strategies.BatchedIngestStrategy] constructor:

```python
ingest_strategy = BatchedIngestStrategy(batch_size=64)
```