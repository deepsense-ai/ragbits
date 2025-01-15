"""
Ragbits Document Search Example: Chroma x OpenTelemetry

This example demonstrates how to use the `DocumentSearch` class to search for documents with a more advanced setup.
We will use the `LiteLLMEmbeddings` class to embed the documents and the query, the `ChromaVectorStore` class to store
the embeddings, and the OpenTelemetry SDK to trace the operations.

The script performs the following steps:

    1. Create a list of documents.
    2. Initialize the `LiteLLMEmbeddings` class with the OpenAI `text-embedding-3-small` embedding model.
    3. Initialize the `ChromaVectorStore` class with a `PersistentClient` instance and an index name.
    4. Initialize the `DocumentSearch` class with the embedder and the vector store.
    5. Ingest the documents into the `DocumentSearch` instance.
    6. List all documents in the vector store.
    7. Search for documents using a query.
    8. Print the list of all documents and the search results.

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/chroma_otel.py
    ```

The script exports traces to the local OTLP collector running on `http://localhost:4317`. To visualize the traces,
you can use Jeager. The recommended way to run it is using the official Docker image:

    1. Run Jaeger Docker container:

        ```bash
        docker run -d --rm --name jaeger \
            -p 16686:16686 \
            -p 4317:4317 \
            jaegertracing/all-in-one:1.62.0
        ```

    2. Open the Jaeger UI in your browser:

        ```
        http://localhost:16686
        ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[chroma,otel]",
# ]
# ///

import asyncio

from chromadb import EphemeralClient
from chroma_opentelemetry import trace
from chroma_opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from chroma_opentelemetry.sdk.resources import SERVICE_NAME, Resource
from chroma_opentelemetry.sdk.trace import TracerProvider
from chroma_opentelemetry.sdk.trace.export import BatchSpanProcessor

from ragbits.core import audit
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.document_search import DocumentSearch, SearchConfig
from ragbits.document_search.documents.document import DocumentMeta

provider = TracerProvider(resource=Resource({SERVICE_NAME: "ragbits"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter("http://localhost:4317", insecure=True)))
trace.set_tracer_provider(provider)

audit.set_trace_handlers("otel")

documents = [
    DocumentMeta.create_text_document_from_literal(
        """
        RIP boiled water. You will be mist.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        Why doesn't James Bond fart in bed? Because it would blow his cover.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        Why programmers don't like to swim? Because they're scared of the floating points.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        This one is completely unrelated.
        """
    ),
]


async def main() -> None:
    """
    Run the example.
    """
    embedder = LiteLLMEmbeddings(
        model="text-embedding-3-small",
    )
    vector_store = ChromaVectorStore(
        client=EphemeralClient(),
        index_name="jokes",
    )
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )

    await document_search.ingest(documents)

    all_documents = await vector_store.list()

    print()
    print("All documents:")
    print([doc.metadata["content"] for doc in all_documents])

    query = "I'm boiling my water and I need a joke"
    vector_store_kwargs = {
        "k": 2,
        "max_distance": None,
    }
    results = await document_search.search(
        query,
        config=SearchConfig(vector_store_kwargs=vector_store_kwargs),
    )

    print()
    print(f"Documents similar to: {query}")
    print([element.text_representation for element in results])


if __name__ == "__main__":
    asyncio.run(main())
