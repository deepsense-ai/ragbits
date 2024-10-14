import tempfile
from pathlib import Path
from typing import Union
from unittest.mock import AsyncMock

import pytest

from ragbits.core.vector_store.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search._main import SearchConfig
from ragbits.document_search.documents.document import Document, DocumentMeta, DocumentType
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.documents.sources import LocalFileSource
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.dummy import DummyProvider


async def test_document_search_ingest_document_from_source():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    providers = {DocumentType.TXT: DummyProvider()}
    router = DocumentProcessorRouter.from_config(providers)

    document_search = DocumentSearch(
        embedder=embeddings_mock, vector_store=InMemoryVectorStore(), document_processor_router=router
    )

    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        f.write(b"Name of Peppa's brother is George")
        f.seek(0)

        source = LocalFileSource(path=Path(f.name))

        await document_search.ingest_document(source)

        results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"


@pytest.mark.parametrize(
    "document",
    [
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
        Document.from_document_meta(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"), Path("test.txt")
        ),
    ],
)
async def test_document_search_ingest_document(document: Union[DocumentMeta, Document]):
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search = DocumentSearch(embedder=embeddings_mock, vector_store=InMemoryVectorStore())

    await document_search.ingest_document(document, document_processor=DummyProvider())

    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"


async def test_document_search_insert_elements():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search = DocumentSearch(embedder=embeddings_mock, vector_store=InMemoryVectorStore())

    await document_search.insert_elements(
        [
            TextElement(
                content="Name of Peppa's brother is George",
                document_meta=DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
            )
        ]
    )

    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"


async def test_document_search_with_no_results():
    document_search = DocumentSearch(embedder=AsyncMock(), vector_store=InMemoryVectorStore())

    results = await document_search.search("Peppa's sister")

    assert not results


async def test_document_search_with_search_config():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search = DocumentSearch(embedder=embeddings_mock, vector_store=InMemoryVectorStore())

    await document_search.ingest_document(
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
        document_processor=DummyProvider(),
    )

    results = await document_search.search("Peppa's brother", search_config=SearchConfig(vector_store_kwargs={"k": 1}))

    assert len(results) == 1
    assert results[0].content == "Name of Peppa's brother is George"
