from ragbits.core.embeddings.noop import NoopEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore, VectorStoreOptions
from ragbits.document_search import DocumentSearch


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
