from ragbits.core.embeddings.noop import NoopEmbeddings
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.vector_store.in_memory import InMemoryVectorStore

CONFIG = {
    "embedder": {"type": "NoopEmbeddings"},
    "vector_store": {
        "type": "packages.ragbits-document-search.src.ragbits.document_search.vector_store.in_memory:InMemoryVectorStore"
    },
    "reranker": {"type": "NoopReranker"},
}


async def test_document_search():
    document_search = DocumentSearch(embedder=NoopEmbeddings(), vector_store=InMemoryVectorStore())

    await document_search.ingest_document(
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")
    )

    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"


async def test_document_search_from_config():
    document_search = DocumentSearch.from_config(CONFIG)

    await document_search.ingest_document(
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")
    )

    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"
