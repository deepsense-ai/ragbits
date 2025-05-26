import asyncio

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore, VectorStoreOptions
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.retrieval.rerankers.base import RerankerOptions
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker


def create_document_search_instance_223():
    vector_store_options = VectorStoreOptions(k=223)
    document_search: DocumentSearch = DocumentSearch(
        reranker=NoopReranker(default_options=RerankerOptions(top_n=223)),
        vector_store=InMemoryVectorStore(embedder=NoopEmbedder(), default_options=vector_store_options),
    )
    return document_search


def create_document_search_instance_825():
    vector_store_options = VectorStoreOptions(k=825)
    document_search: DocumentSearch = DocumentSearch(
        reranker=NoopReranker(default_options=RerankerOptions(top_n=825)),
        vector_store=InMemoryVectorStore(embedder=NoopEmbedder(), default_options=vector_store_options),
    )
    return document_search


async def _add_example_documents(document_search: DocumentSearch) -> None:
    documents = [
        DocumentMeta.from_literal("Foo document"),
        DocumentMeta.from_literal("Bar document"),
        DocumentMeta.from_literal("Baz document"),
    ]
    await document_search.ingest(documents)


def create_document_search_instance_with_documents():
    document_search: DocumentSearch = DocumentSearch(vector_store=InMemoryVectorStore(embedder=NoopEmbedder()))
    asyncio.run(_add_example_documents(document_search))
    return document_search
