from unittest.mock import AsyncMock

from ragbits.core.vector_store.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement


async def test_document_search():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search = DocumentSearch(embedder=embeddings_mock, vector_store=InMemoryVectorStore())

    await document_search.ingest_document(
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")
    )

    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"
