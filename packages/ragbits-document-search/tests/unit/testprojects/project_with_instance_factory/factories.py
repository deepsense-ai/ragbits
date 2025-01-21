import asyncio

from ragbits.core.embeddings.noop import NoopEmbeddings
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
