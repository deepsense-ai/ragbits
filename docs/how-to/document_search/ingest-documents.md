# How-To: Ingest Documents

The Ragbits document ingest pipeline consists of four main steps: loading, parsing, enrichment, and indexing. All of these steps can be orchestrated using different strategies, depending on the expected load.

## Loading dataset

Before processing a document in Ragbits, it must first be defined and downloaded. This can be done in several ways: by specifying a source URI or using an instance of [`Source`][ragbits.core.sources.base.Source], [`DocumentMeta`][ragbits.document_search.documents.document.DocumentMeta] or [`Document`][ragbits.document_search.documents.document.Document].

=== "URI"

    ```python
    from ragbits.document_search import DocumentSearch

    document_search = DocumentSearch(...)

    await document_search.ingest("s3://")
    ```

=== "Source"

    ```python
    from ragbits.core.sources import WebSource
    from ragbits.document_search import DocumentSearch

    document_search = DocumentSearch(...)

    await document_search.ingest([WebSource(...), ...])
    ```

=== "Metadata"

    ```python
    from ragbits.document_search.documents.document import DocumentMeta
    from ragbits.document_search import DocumentSearch

    document_search = DocumentSearch(...)

    await document_search.ingest([DocumentMeta.from_local_path(...), ...])
    ```

=== "Document"

    ```python
    from ragbits.document_search.documents.document import Document
    from ragbits.document_search import DocumentSearch

    document_search = DocumentSearch(...)

    await document_search.ingest([Document(...), ...])
    ```

All sources supported by Ragbits are available [here](../sources/load-dataset.md#supported-sources).

## Parsing documents

Depending on the document type, different parsers operate in the background to convert the document into a list of elements. Ragbits primarily relies on the [`docling`](https://github.com/docling-project/docling) library, which supports parsing and chunking for most common document formats (e.g., PDF, Markdown, DOCX, JPG).

To define a new parser, extend the [`DocumentParser`][ragbits.document_search.ingestion.parsers.base.DocumentParser] class.

```python
from bs4 import BeautifulSoup
from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.parsers import DocumentParser


class HTMLDocumentParser(DocumentParser):
    """
    Parser that uses the Beautiful Soup to process the documents.
    """

    supported_document_types = {DocumentType.HTML}

    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the HTML document using the Beautiful Soup.

        Args:
            document: The document to parse.

        Returns:
            The list of elements extracted from the document.
        """
        dom = BeautifulSoup(document.local_path.read_text(), "html.parser")
        ...
        return [
            TextElement(document_meta=document.metadata, ...),
            ...
        ]
```

To apply the new parser, define a [`DocumentParserRouter`][ragbits.document_search.ingestion.parsers.DocumentParserRouter] and assign it to the [`DocumentSearch`][ragbits.document_search.DocumentSearch] instance.

```python
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.ingestion.parsers import DocumentParserRouter

parser_router = DocumentParserRouter({
    DocumentType.HTML: HTMLDocumentParser(),
    ...
})
document_search = DocumentSearch(parser_router=parser_router, ...)
```

## Enriching elements

After parsing the document, the resulting elements can optionally be enriched. Element enrichers generate additional information about elements, such as text summaries or image descriptions. Most enrichers are lightweight wrappers around LLMs that process elements in a specific format. By default, Ragbits enriches image elements with descriptions using the preferred VLM.

To define a new enricher, extend the [`ElementEnricher`][ragbits.document_search.ingestion.enrichers.base.ElementEnricher] class.

```python
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.ingestion.enrichers import ElementEnricher


class TextElementEnricher(ElementEnricher[TextElement]):
    """
    Enricher that summarizes text elements using LLM.
    """

    async def enrich(self, elements: list[TextElement]) -> list[TextElement]:
        """
        Enrich text elements with the text summary.

        Args:
            elements: The text elements to be enriched.

        Returns:
            The list of enriched text elements.
        """
        responses = await llm.generate(TextSummarizerPrompt(...))
        ...
        return [
            TextElement(
                document_meta=element.document_meta,
                content=...,
            ),
            ...
        ]
```

To apply the new enricher, define a [`ElementEnricherRouter`][ragbits.document_search.ingestion.enrichers.ElementEnricherRouter] and assign it to the [`DocumentSearch`][ragbits.document_search.DocumentSearch] instance.

```python
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.ingestion.enrichers import ElementEnricherRouter

enricher_router = ElementEnricherRouter({
    TextElement: TextElementEnricher(),
    ...
})
document_search = DocumentSearch(enricher_router=enricher_router, ...)
```

## Indexing elements

At the end of the ingestion process, elements are indexed into the vector database. First, the vector store is scanned to identify and remove any existing elements from sources that are about to be ingested. Then, the new elements are inserted, ensuring that only the latest versions of the sources remain. Indexing is performed in batches, allowing all elements from a batch of documents to be processed in a single request to the database, which improves efficiency and speeds up the process.

## Orchestrating ingest tasks

Running an ingest pipeline can be time-consuming, depending on your expected load. Ragbits offers three built-in ingest strategies that you can use out of the box for your workload, or you can implement a custom strategy to suit your needs.

=== "Sequential"

    ```python
    from ragbits.document_search import DocumentSearch
    from ragbits.document_search.ingestion.strategies import SequentialIngestStrategy

    ingest_strategy = SequentialIngestStrategy()
    document_search = DocumentSearch(ingest_strategy=ingest_strategy, ...)

    await document_search.ingest("s3://")
    ```

    The default ingest strategy in Ragbits is [`SequentialIngestStrategy`][ragbits.document_search.ingestion.strategies.SequentialIngestStrategy]. This strategy processes documents one by one, waiting for each document to be processed before moving on to the next. Although it's the simplest and most straightforward strategy, it may be slow when processing a large number of documents.

=== "Batched"

    ```python
    from ragbits.document_search import DocumentSearch
    from ragbits.document_search.ingestion.strategies import BatchedIngestStrategy

    ingest_strategy = BatchedIngestStrategy(batch_size=10)
    document_search = DocumentSearch(ingest_strategy=ingest_strategy, ...)

    await document_search.ingest("s3://")
    ```

    If you need to process documents simultaneously, you can use the [`BatchedIngestStrategy`][ragbits.document_search.ingestion.strategies.BatchedIngestStrategy] strategy. This strategy uses Python built-in `asyncio` to process documents concurrently, making it faster than the [`SequentialIngestStrategy`][ragbits.document_search.ingestion.strategies.SequentialIngestStrategy] strategy, especially with large document volumes.

=== "Ray Distributed"

    ```python
    from ragbits.document_search import DocumentSearch
    from ragbits.document_search.ingestion.strategies import RayDistributedIngestStrategy

    ingest_strategy = RayDistributedIngestStrategy(cpu_batch_size=1, io_batch_size=5)
    document_search = DocumentSearch(ingest_strategy=ingest_strategy, ...)

    await document_search.ingest("s3://")
    ```

    If you need even better performance, you can use the [`RayDistributedIngestStrategy`][ragbits.document_search.ingestion.strategies.RayDistributedIngestStrategy] strategy. By default, when run outside of a Ray cluster, the Ray Core library will parallelize the processing of documents on the local machine, using available CPU cores.

    When run inside a Ray cluster, the Ray Core library will parallelize the processing of documents across the nodes in the cluster. There are several ways of sending documents to the Ray cluster for processing, but using Ray Jobs API is by far the most recommended one.

    To use Ray Jobs API, you should prepare the processing script and the documents to be processed, and then submit the job to the Ray cluster.
    Make sure to replace `<cluster_address>` with the address of your Ray cluster and adjust the `entrypoint` and `runtime_env` parameters to match your setup.

    ```python
    from ray.job_submission import JobSubmissionClient

    client = JobSubmissionClient("http://<cluster_address>:8265")
    client.submit_job(
        entrypoint="python script.py",
        runtime_env={
            "working_dir": "./",
            "pip": [
                "ragbits-core",
                "ragbits-document-search[ray]"
            ]
        },
    )
    ```

    Ray Jobs is also available as CLI commands. You can submit a job using the following command:

    ```bash
    ray job submit \
        --address http://<cluster_address>:8265 \
        --runtime-env '{"pip": ["ragbits-core", "ragbits-document-search[ray]"]}' \
        --working-dir . \
        -- python script.py
    ```

    There are also other ways to submit jobs to the Ray cluster. For more information, please refer to the [Ray documentation](https://docs.ray.io/en/latest/ray-overview/index.html).

To define a new ingest strategy, extend the [`IngestStrategy`][ragbits.document_search.ingestion.strategies.IngestStrategy] class.

```python
from ragbits.core.vector_stores import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.core.sources import Source
from ragbits.document_search.ingestion.enrichers import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers import DocumentParserRouter
from ragbits.document_search.ingestion.strategies import (
    IngestDocumentResult,
    IngestError,
    IngestExecutionResult,
    IngestStrategy,
)


class DelayedIngestStrategy(IngestStrategy):
    """
    Ingest strategy that processes documents in sequence, one at a time with a small delay.
    """

    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        parser_router: DocumentParserRouter,
        enricher_router: ElementEnricherRouter,
    ) -> IngestExecutionResult:
        """
        Ingest documents sequentially one by one with a small delay.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            parser_router: The document parser router to use.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The ingest execution result.
        """
        results = IngestExecutionResult()

        for document in documents:
            try:
                # Parse
                parsed_elements = await self._call_with_error_handling(self._parse_document, ...)

                # Enrich
                enriched_elements = await self._call_with_error_handling(self._enrich_elements, ...)

                # Index
                await self._call_with_error_handling(self._remove_elements, ...)
                await self._call_with_error_handling(self._insert_elements, ...)

                # Artificial delay
                await asyncio.sleep(1)

            except Exception as exc:
                results.failed.append(IngestDocumentResult(error=IngestError.from_exception(exc), ...))
            else:
                results.successful.append(IngestDocumentResult(...))

        return results
```
