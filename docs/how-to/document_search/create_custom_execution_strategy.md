# How to Create a Custom Execution Strategy

!!! note
    To learn how to use a built-in asynchronous execution strategy, see [How to Ingest Documents Asynchronously](async_processing.md).

In Ragbits, document processing during ingestion is controlled by a component known as "processing execution strategy". It doesn't deal with the actual processing of documents, but rather, it orchestrates how the processing is executed.

Ragbits provides several built-in execution strategies that can be easily interchanged. You can also create your own custom execution strategy to fulfill your specific needs. This guide will show you how to develop a custom execution strategy using a somewhat impractical example of a strategy that processes documents one by one, but with a delay between each document.

## Implementing a Custom Execution Strategy
To create a custom execution strategy, you need to create a new class that inherits from [`ProcessingExecutionStrategy`][ragbits.document_search.ingestion.processor_strategies.ProcessingExecutionStrategy] and implement the abstract method `execute`. This method should take a list of documents and process them asynchronously. It should also implement the abstract method `process_documents`.

While implementing the `process_documents` method, you can use the built-in `process_document` method, which has the same signature and performs the actual processing of a single document.

```python
import asyncio
from collections.abc import Sequence

from ragbits.document_search.documents.document import Document, DocumentMeta, Source
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies import ProcessingExecutionStrategy
from ragbits.document_search.ingestion.providers.base import BaseProvider

class DelayedExecutionStrategy(ProcessingExecutionStrategy):
    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        elements = []
        for document in documents:
            await asyncio.sleep(1)
            element = await self.process_document(document, processor_router, processor_overwrite)
            elements.append(element)
        return elements
```

## Implementing an Advanced Custom Execution Strategy
Alternatively, instead of using the `process_document` method, you can process documents directly using the `processor_router` and `processor_overwrite` parameters. This gives you more control over the processing of documents.

```python
import asyncio

from ragbits.document_search.ingestion.processor_strategies import ProcessingExecutionStrategy

class DelayedExecutionStrategy(ProcessingExecutionStrategy):
    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        elements = []
        for document in documents:
            # Convert the document to DocumentMeta
            document_meta = await self.to_document_meta(document)

            # Get the processor for the document
            processor = processor_overwrite or processor_router.get_processor(document)

            await asyncio.sleep(1)

            element = await processor.process(document_meta)
            elements.append(element)
        return elements
```

## Using the Custom Execution Strategy
To use your custom execution strategy, you need to specify it when creating the [`DocumentSearch`][ragbits.document_search.DocumentSearch] instance:

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
vector_store = InMemoryVectorStore()
processing_strategy = DelayedExecutionStrategy()

document_search = DocumentSearch(
    embedder=embedder,
    vector_store=vector_store,
    processing_strategy=processing_strategy
)
```