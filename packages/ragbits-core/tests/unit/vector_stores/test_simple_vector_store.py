from pathlib import Path

from ragbits.core.vector_store.in_memory import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.documents.sources import LocalFileSource


async def test_simple_vector_store():
    store = InMemoryVectorStore()

    document_meta = DocumentMeta(document_type=DocumentType.TXT, source=LocalFileSource(path=Path("test.txt")))
    elements = [
        (TextElement(content="dog", document_meta=document_meta), [0.5, 0.5]),
        (TextElement(content="cat", document_meta=document_meta), [0.6, 0.6]),
    ]

    entries = [element[0].to_vector_db_entry(vector=element[1]) for element in elements]

    await store.store(entries)

    search_vector = [0.4, 0.4]

    results = await store.retrieve(search_vector, 2)

    assert len(results) == 2
    assert results[0].metadata["content"] == "dog"
    assert results[1].metadata["content"] == "cat"
