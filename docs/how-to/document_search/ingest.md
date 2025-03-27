# How-To: Ingest Documents

The Ragbits document ingest pipeline consists of four main steps: loading, parsing, enrichment, and indexing. All of these steps can be orchestrated using different strategies, depending on the expected load.

## Loading

Before a document can be processed, it must be defined and downloaded. In Ragbits, there are a few ways to do this: you can provide a source URI, or a source instance.

```python
from ragbits.document_search.documents.sources import WebSource
from ragbits.document_search import DocumentSearch

document_search = DocumentSearch(...)

await document_search.ingest("s3://")
await document_search.ingest([WebSource(...), ...])
```

There are multiple ways to define a document depending on the available data. You can explore the full API [`here`][ragbits.document_search.DocumentSearch.ingest] or check the provided [examples](https://github.com/deepsense-ai/ragbits/tree/main/examples/document-search). Generally, the key idea is to supply metadata about the document's location, and Ragbits will handle the rest.

Ragbits supports various popular data sources, including S3, GSC, and Azure Blob Storage. You can also add support for custom sources by extending the [`Source`][ragbits.document_search.documents.sources.Source] class.

```python
from ragbits.document_search.documents.sources import Source


class CustomSource(Source):
    """
    Source that downloads file from the web.
    """

    protocol: ClassVar[str] = "custom"
    source_url: str
    ...

    @property
    def id(self) -> str:
        return f"{self.protocol}:{self.source_url}"

    @classmethod
    async def from_uri(cls, uri: str) -> list[Self]:
        """
        Create source instances from a URI path.

        Args:
            uri: The URI path.

        Returns:
            The list of sources.
        """
        return [cls(...), ...]

    async def fetch(self) -> Path:
        """
        Download a file for the given url.

        Returns:
            The local path to the downloaded file.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(self.source_url) as response:
                with open(f"/tmp/{self.source_url}", "w") as f:
                    f.write(await response.text())
        ...
        return Path(f"/tmp/{self.source_url}")
```

## Parsing

Depending on the document type, different parsers operate in the background to convert the document into a list of elements. Ragbits primarily relies on the  [`unstructured`](https://github.com/Unstructured-IO/unstructured) library, which supports parsing and chunking for most common document formats (e.g., PDF, Markdown, DOC, JPG). If you need to implement a custom parser, you must extend the [`DocumentParser`][ragbits.document_search.ingestion.parsers.base.DocumentParser] class.

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

To apply the new parser, define a parser router and assign it to the document search instance.

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

## Enrichment

After parsing the document, the resulting elements can optionally be enriched. Element enrichers generate additional information about elements, such as text summaries or image descriptions. Most enrichers are lightweight wrappers around LLMs that process elements in a specific format. By default, Ragbit enriches image elements with descriptions using the preferred VLM. To define a new element enricher, extend the [`ElementEnricher`][ragbits.document_search.ingestion.enrichers.base.ElementEnricher] class.

```python
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.ingestion.enrichers import ElementEnricher


class TextElementEnricher(ElementEnricher[TextElement]):
    """
    Enricher that sumarizes text elements using LLM.
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

To apply the new enriche, define a enricher router and assign it to the document search instance:

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

## Indexing

At the end of the ingestion process, elements are indexed into the vector database. First, the vector store is scanned to identify and remove any existing elements from sources that are about to be ingested. Then, the new elements are inserted, ensuring that only the latest versions of the sources remain. Indexing is performed in batches, allowing all elements from a batch of documents to be processed in a single request to the database, which improves efficiency and speeds up the process.

## Strategies

Running an ingest pipeline can be time-consuming, depending on your expected load. Ragbits offers three built-in ingest strategies that you can use out of the box for your workload, or you can implement a custom strategy to suit your needs.

### Sequential Ingest

...

### Batched Ingest

...

### Ray Distributed Ingest

...

### Custom Ingest

...
