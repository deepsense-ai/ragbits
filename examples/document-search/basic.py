# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[litellm,otel]",
# ]
# ///
import asyncio

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from ragbits.core import audit
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

provider = TracerProvider(resource=Resource({SERVICE_NAME: "ragbits"}))
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
# provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter("http://localhost:4317", insecure=True)))
trace.set_tracer_provider(provider)

audit.set_trace_handlers("otel")
# audit.set_trace_handlers(["langsmith", "otel"])
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
]


async def main() -> None:
    """
    Run the example.
    """
    embedder = LiteLLMEmbeddings(
        model="text-embedding-3-small",
    )
    vector_store = InMemoryVectorStore()
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )

    await document_search.ingest(documents)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
