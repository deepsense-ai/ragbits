import tempfile
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search._main import SearchConfig
from ragbits.document_search.documents.document import Document, DocumentMeta, DocumentType
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.documents.sources import LocalFileSource
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies.batched import BatchedAsyncProcessing
from ragbits.document_search.ingestion.providers import BaseProvider
from ragbits.document_search.ingestion.providers.dummy import DummyProvider

CONFIG = {
    "embedder": {"type": "NoopEmbeddings"},
    "vector_store": {"type": "ragbits.core.vector_stores.in_memory:InMemoryVectorStore"},
    "reranker": {"type": "NoopReranker"},
    "providers": {"txt": {"type": "DummyProvider"}},
    "processing_strategy": {"type": "SequentialProcessing"},
}


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
            "Name of Peppa's brother is George",
        ),
        (
            Document.from_document_meta(
                DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"), Path("test.txt")
            ),
            "Name of Peppa's brother is George",
        ),
    ],
)
async def test_document_search_from_config(document: DocumentMeta, expected: str):
    document_search = DocumentSearch.from_config(CONFIG)

    await document_search.ingest([document])
    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == expected  # type: ignore


async def test_document_search_ingest_from_source():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    providers: dict[DocumentType, Callable[[], BaseProvider] | BaseProvider] = {DocumentType.TXT: DummyProvider()}
    router = DocumentProcessorRouter.from_config(providers)

    document_search = DocumentSearch(
        embedder=embeddings_mock, vector_store=InMemoryVectorStore(), document_processor_router=router
    )

    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        f.write(b"Name of Peppa's brother is George")
        f.seek(0)

        source = LocalFileSource(path=Path(f.name))

        await document_search.ingest([source])

        results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"  # type: ignore


@pytest.mark.parametrize(
    "document",
    [
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
        Document.from_document_meta(
            DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
            Path("test.txt"),
        ),
    ],
)
async def test_document_search_ingest(document: DocumentMeta | Document):
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search = DocumentSearch(embedder=embeddings_mock, vector_store=InMemoryVectorStore())

    await document_search.ingest([document], document_processor=DummyProvider())

    results = await document_search.search("Peppa's brother")

    first_result = results[0]

    assert isinstance(first_result, TextElement)
    assert first_result.content == "Name of Peppa's brother is George"  # type: ignore


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
    assert first_result.content == "Name of Peppa's brother is George"  # type: ignore


async def test_document_search_with_no_results():
    document_search = DocumentSearch(embedder=AsyncMock(), vector_store=InMemoryVectorStore())

    results = await document_search.search("Peppa's sister")

    assert not results


async def test_document_search_with_search_config():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search = DocumentSearch(embedder=embeddings_mock, vector_store=InMemoryVectorStore())

    await document_search.ingest(
        [DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")],
        document_processor=DummyProvider(),
    )

    results = await document_search.search("Peppa's brother", config=SearchConfig(vector_store_kwargs={"k": 1}))

    assert len(results) == 1
    assert results[0].content == "Name of Peppa's brother is George"  # type: ignore


async def test_document_search_ingest_multiple_from_sources():
    document_search = DocumentSearch.from_config(CONFIG)
    examples_files = Path(__file__).parent / "example_files"

    await document_search.ingest(
        LocalFileSource.list_sources(examples_files, file_pattern="*.md"),
        document_processor=DummyProvider(),
    )

    results = await document_search.search("foo")

    assert len(results) == 2
    assert {result.content for result in results} == {"foo", "bar"}  # type: ignore


async def test_document_search_with_batched():
    documents = [
        DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's father is Daddy Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's mother is Mummy Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's friend is Suzy Sheep"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's friend is Danny Dog"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's friend is Pedro Pony"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's friend is Emily Elephant"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's friend is Candy Cat"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's teacher is Madame Gazelle"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's doctor is Dr. Brown Bear"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's cousin is Chloe Pig"),
        DocumentMeta.create_text_document_from_literal("Name of Peppa's cousin is Alexander Pig"),
    ]

    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]] * len(documents)

    processing_strategy = BatchedAsyncProcessing(batch_size=5)
    vectore_store = InMemoryVectorStore()

    document_search = DocumentSearch(
        embedder=embeddings_mock,
        vector_store=vectore_store,
        processing_strategy=processing_strategy,
    )

    await document_search.ingest(documents)

    results = await document_search.search("Peppa's brother", config=SearchConfig(vector_store_kwargs={"k": 100}))

    assert len(await vectore_store.list()) == 12
    assert len(results) == 12
