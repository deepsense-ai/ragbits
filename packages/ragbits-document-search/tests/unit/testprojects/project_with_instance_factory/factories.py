import asyncio

from ragbits.core.embeddings.dummy import DummyEmbeddings
from ragbits.core.embeddings.noop import NoopEmbeddings
from ragbits.core.processing_strategy.sequential import SequentialProcessing
from ragbits.core.query_rephraser.noop import NoopQueryRephraser
from ragbits.core.reranker.noop import NoopReranker
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore, VectorStoreOptions
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta


def create_document_search_instance_223():
    vector_store_options = VectorStoreOptions(k=223)
    document_search = DocumentSearch(
        embedder=NoopEmbeddings(), vector_store=InMemoryVectorStore(default_options=vector_store_options)
    )
    return document_search


def create_document_search_instance_825():
    vector_store_options = VectorStoreOptions(k=825)
    document_search = DocumentSearch(
        embedder=NoopEmbeddings(), vector_store=InMemoryVectorStore(default_options=vector_store_options)
    )
    return document_search


async def _add_example_documents(document_search: DocumentSearch) -> None:
    documents = [
        DocumentMeta.create_text_document_from_literal("Foo document"),
        DocumentMeta.create_text_document_from_literal("Bar document"),
        DocumentMeta.create_text_document_from_literal("Baz document"),
    ]
    await document_search.ingest(documents)


def create_document_search_instance_with_documents():
    document_search = DocumentSearch(embedder=NoopEmbeddings(), vector_store=InMemoryVectorStore())
    asyncio.run(_add_example_documents(document_search))
    return document_search


def create_document_search() -> DocumentSearch:
    """Create a document search instance."""
    vector_store = InMemoryVectorStore(
        default_embedder=DummyEmbeddings(),
    )
    return DocumentSearch(
        vector_store=vector_store,
        rephraser=NoopQueryRephraser(),
        reranker=NoopReranker(),
        processing_strategy=SequentialProcessing(),
    )


def create_document_search_with_config() -> DocumentSearch:
    """Create a document search instance with config."""
    config = {
        "vector_store": {
            "type": "InMemoryVectorStore",
            "config": {
                "default_embedder": {
                    "type": "DummyEmbeddings",
                    "config": {},
                },
            },
        },
        "rephraser": {"type": "NoopQueryRephraser"},
        "reranker": {"type": "NoopReranker"},
        "processing_strategy": {"type": "SequentialProcessing"},
    }
    return DocumentSearch.from_config(config)
