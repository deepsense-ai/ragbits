import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.sources.gcs import GCSSource
from ragbits.core.sources.local import LocalFileSource
from ragbits.core.vector_stores.base import VectorStoreOptions, VectorStoreResult
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search._main import DocumentSearch, DocumentSearchOptions
from ragbits.document_search.documents.document import (
    Document,
    DocumentMeta,
    DocumentType,
)
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.ingestion.parsers import DocumentParser
from ragbits.document_search.ingestion.parsers.base import TextDocumentParser
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.strategies.batched import BatchedIngestStrategy

CONFIG = {
    "vector_store": {
        "type": "ragbits.core.vector_stores.in_memory:InMemoryVectorStore",
        "config": {
            "embedder": {"type": "NoopEmbedder"},
        },
    },
    "reranker": {"type": "NoopReranker"},
    "parsers": {"txt": {"type": "TextDocumentParser"}},
    "ingest_strategy": {"type": "SequentialIngestStrategy"},
}


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (
            DocumentMeta.from_literal("Name of Peppa's brother is George"),
            "Name of Peppa's brother is George",
        ),
        (
            Document.from_document_meta(
                DocumentMeta.from_literal("Name of Peppa's brother is George"), Path("test.txt")
            ),
            "Name of Peppa's brother is George",
        ),
    ],
)
async def test_document_search_from_config(document: DocumentMeta, expected: str):
    document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)

    await document_search.ingest([document])

    results = await document_search.search("Peppa's brother")

    assert isinstance(results[0], TextElement)
    assert results[0].content == expected


async def test_document_search_ingest_from_source():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    document_search: DocumentSearch = DocumentSearch(
        vector_store=InMemoryVectorStore(embedder=embeddings_mock),
        parser_router=DocumentParserRouter({DocumentType.TXT: TextDocumentParser()}),
    )

    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        f.write(b"Name of Peppa's brother is George")
        f.seek(0)
        source = LocalFileSource(path=Path(f.name))
        await document_search.ingest([source])

    results = await document_search.search("Peppa's brother")

    assert isinstance(results[0], TextElement)
    assert results[0].content == "Name of Peppa's brother is George"


@pytest.mark.parametrize(
    "document",
    [
        DocumentMeta.from_literal("Name of Peppa's brother is George"),
        Document.from_document_meta(
            DocumentMeta.from_literal("Name of Peppa's brother is George"),
            Path("test.txt"),
        ),
    ],
)
async def test_document_search_ingest(document: DocumentMeta | Document):
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]
    document_search: DocumentSearch = DocumentSearch(
        vector_store=InMemoryVectorStore(embedder=embeddings_mock),
        parser_router=DocumentParserRouter({DocumentType.TXT: TextDocumentParser()}),
    )
    await document_search.ingest([document])

    results = await document_search.search("Peppa's brother")

    assert isinstance(results[0], TextElement)
    assert results[0].content == "Name of Peppa's brother is George"


async def test_document_search_with_no_results():
    document_search: DocumentSearch = DocumentSearch(vector_store=InMemoryVectorStore(embedder=AsyncMock()))

    results = await document_search.search("Peppa's sister")

    assert not results


async def test_document_search_with_search_config():
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]
    document_search: DocumentSearch = DocumentSearch(
        vector_store=InMemoryVectorStore(embedder=embeddings_mock),
        parser_router=DocumentParserRouter({DocumentType.TXT: TextDocumentParser()}),
    )
    await document_search.ingest([DocumentMeta.from_literal("Name of Peppa's brother is George")])

    results = await document_search.search(
        "Peppa's brother", options=DocumentSearchOptions(vector_store_options=VectorStoreOptions(k=1))
    )

    assert len(results) == 1
    assert isinstance(results[0], TextElement)
    assert cast(TextElement, results[0]).content == "Name of Peppa's brother is George"


async def test_document_search_scores():
    """Test that search results' scores are properly passed to elements."""
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]

    # Create a mock vector store that returns results with scores
    class MockVectorStore(InMemoryVectorStore):
        async def retrieve(
            self,
            text: str,
            options: VectorStoreOptions | None = None,
        ) -> list[VectorStoreResult]:
            results = await super().retrieve(text, options)
            # Add scores to the results
            for i, result in enumerate(results):
                result.score = 0.9 - (i * 0.1)  # Decreasing scores: 0.9, 0.8, 0.7, etc.
            return results

    document_search: DocumentSearch = DocumentSearch(
        vector_store=MockVectorStore(embedder=embeddings_mock),
        parser_router=DocumentParserRouter({DocumentType.TXT: TextDocumentParser()}),
    )

    # Ingest multiple documents
    documents = [
        DocumentMeta.from_literal("First document about Peppa"),
        DocumentMeta.from_literal("Second document about George"),
        DocumentMeta.from_literal("Third document about Peppa and George"),
    ]
    await document_search.ingest(documents)

    # Search and verify scores
    results = await document_search.search(
        "Peppa George", options=DocumentSearchOptions(vector_store_options=VectorStoreOptions(k=3))
    )

    assert len(results) == 3
    assert all(result.score is not None for result in results)
    # Compare scores after ensuring they are not None and casting to float
    scores = [float(result.score) for result in results if result.score is not None]  # type: ignore
    assert scores[0] == 0.9
    assert scores[1] == 0.8
    assert scores[2] == 0.7


async def test_document_search_ingest_multiple_from_sources():
    document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)
    examples_files = Path(__file__).parent.parent / "assets" / "md"

    await document_search.ingest(await LocalFileSource.list_sources(examples_files, file_pattern="*.md"))

    results = await document_search.search("foo")

    assert len(results) == 3
    assert all(isinstance(result, TextElement) for result in results)
    assert {cast(TextElement, result).content for result in results} == {
        "foo",
        "bar",
        "Repository for internal experiment with our upcoming LLM framework.",
    }


async def test_document_search_with_batched():
    documents = [
        DocumentMeta.from_literal("Name of Peppa's brother is George"),
        DocumentMeta.from_literal("Name of Peppa's father is Daddy Pig"),
        DocumentMeta.from_literal("Name of Peppa's mother is Mummy Pig"),
        DocumentMeta.from_literal("Name of Peppa's friend is Suzy Sheep"),
        DocumentMeta.from_literal("Name of Peppa's friend is Danny Dog"),
        DocumentMeta.from_literal("Name of Peppa's friend is Pedro Pony"),
        DocumentMeta.from_literal("Name of Peppa's friend is Emily Elephant"),
        DocumentMeta.from_literal("Name of Peppa's friend is Candy Cat"),
        DocumentMeta.from_literal("Name of Peppa's teacher is Madame Gazelle"),
        DocumentMeta.from_literal("Name of Peppa's doctor is Dr. Brown Bear"),
        DocumentMeta.from_literal("Name of Peppa's cousin is Chloe Pig"),
        DocumentMeta.from_literal("Name of Peppa's cousin is Alexander Pig"),
    ]

    ingest_strategy = BatchedIngestStrategy(batch_size=5)
    vectore_store = InMemoryVectorStore(embedder=NoopEmbedder())

    document_search: DocumentSearch = DocumentSearch(
        vector_store=vectore_store,
        ingest_strategy=ingest_strategy,
    )

    await document_search.ingest(documents)

    results = await document_search.search(
        "Peppa's brother", options=DocumentSearchOptions(vector_store_options=VectorStoreOptions(k=100))
    )

    assert len(await vectore_store.list()) == 12
    assert len(results) == 12


@pytest.mark.asyncio
async def test_document_search_ingest_from_uri_basic():
    # Setup
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Test content")

        document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)

        # Test ingesting from URI
        await document_search.ingest(f"local://{test_file}")

        # Verify
        results = await document_search.search("Test content")
        assert len(results) == 1
        assert isinstance(results[0], TextElement)
        assert isinstance(results[0].document_meta.source, LocalFileSource)
        assert str(cast(LocalFileSource, results[0].document_meta.source).path) == str(test_file)
        assert results[0].content == "Test content"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pattern", "dir_pattern", "search_query", "expected_contents", "expected_filenames"),
    [
        (
            "test*.txt",
            None,
            "test content",  # We search for "test content"
            {"First test content", "Second test content"},
            {"test1.txt", "test2.txt"},
        ),
        (
            "othe?.txt",
            None,
            "Other content",
            {"Other content"},
            {"other.txt"},
        ),
        (
            "te??*.txt",
            "**",
            "test content",  # We search for "test content"
            {"First test content", "Second test content"},
            {"test1.txt", "test2.txt"},
        ),
    ],
)
async def test_document_search_ingest_from_uri_with_wildcard(
    pattern: str, dir_pattern: str | None, search_query: str, expected_contents: set, expected_filenames: set
):
    # Setup temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple test files
        test_files = [
            (Path(temp_dir) / "test1.txt", "First test content"),
            (Path(temp_dir) / "test2.txt", "Second test content"),
            (Path(temp_dir) / "other.txt", "Other content"),
        ]
        for file_path, content in test_files:
            file_path.write_text(content)

        document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)

        # Use the parametrized glob pattern
        dir_pattern = f"{str(Path(temp_dir).parent)}/{dir_pattern}" if dir_pattern is not None else temp_dir
        await document_search.ingest(f"local://{dir_pattern}/{pattern}")

        # Perform the search
        results = await document_search.search(search_query)

        # Check that we have the expected number of results
        assert len(results) == len(
            expected_contents
        ), f"Expected {len(expected_contents)} result(s) but got {len(results)}"

        # Verify each result is a TextElement
        assert all(isinstance(result, TextElement) for result in results)

        # Collect the actual text contents
        contents = {cast(TextElement, result).content for result in results}
        assert contents == expected_contents, f"Expected contents: {expected_contents}, got: {contents}"

        # Verify the sources (file paths) match
        sources = {str(cast(LocalFileSource, result.document_meta.source).path).split("/")[-1] for result in results}
        # We compare only the filenames; if you need full paths, compare the full str(...) instead
        assert sources == expected_filenames, f"Expected sources: {expected_filenames}, got: {sources}"


@pytest.mark.asyncio
async def test_document_search_ingest_from_gcs_uri_basic():
    # Create mock storage client
    storage_mock = mock.AsyncMock()
    storage_mock.download = mock.AsyncMock(return_value=b"GCS test content")
    storage_mock.list_objects = mock.AsyncMock(
        return_value={"items": [{"name": "folder/test1.txt"}, {"name": "folder/test2.txt"}]}
    )
    storage_mock.__aenter__ = mock.AsyncMock(return_value=storage_mock)
    storage_mock.__aexit__ = mock.AsyncMock()

    # Create mock storage factory
    mock_storage = mock.Mock()
    mock_storage.return_value = storage_mock

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up local storage dir
        os.environ["LOCAL_STORAGE_DIR"] = temp_dir

        # Inject the mock storage
        GCSSource.set_storage(mock_storage())

        document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)

        # Test single file
        await document_search.ingest("gcs://test-bucket/folder/test1.txt")
        results = await document_search.search("GCS test content")
        assert len(results) == 1
        assert isinstance(results[0], TextElement)
        assert results[0].content == "GCS test content"

        # Clean up
        del os.environ["LOCAL_STORAGE_DIR"]


@pytest.mark.asyncio
async def test_document_search_ingest_from_gcs_uri_with_wildcard():
    # Create mock storage client
    storage_mock = mock.AsyncMock()
    storage_mock.download = mock.AsyncMock(side_effect=[b"GCS test content 1", b"GCS test content 2"])
    storage_mock.list_objects = mock.AsyncMock(
        return_value={"items": [{"name": "folder/test1.txt"}, {"name": "folder/test2.txt"}]}
    )
    storage_mock.__aenter__ = mock.AsyncMock(return_value=storage_mock)
    storage_mock.__aexit__ = mock.AsyncMock()

    # Create mock storage factory
    mock_storage = mock.Mock()
    mock_storage.return_value = storage_mock

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up local storage dir
        os.environ["LOCAL_STORAGE_DIR"] = temp_dir

        # Inject the mock storage
        GCSSource.set_storage(mock_storage())

        document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)

        # Test wildcard ingestion
        await document_search.ingest("gcs://test-bucket/folder/*")

        # Verify both files were ingested
        results = await document_search.search("GCS test content")
        assert len(results) == 2

        # Verify first file
        assert isinstance(results[0], TextElement)
        assert results[0].content == "GCS test content 1"

        # Verify second file
        assert isinstance(results[1], TextElement)
        assert results[1].content == "GCS test content 2"

        # Clean up
        storage_mock = mock.AsyncMock()
        storage_mock.download = mock.AsyncMock(return_value=b"")
        storage_mock.list_objects = mock.AsyncMock(return_value={"items": []})
        storage_mock.__aenter__ = mock.AsyncMock(return_value=storage_mock)
        storage_mock.__aexit__ = mock.AsyncMock()
        GCSSource.set_storage(storage_mock)
        del os.environ["LOCAL_STORAGE_DIR"]


@pytest.mark.asyncio
async def test_document_search_ingest_from_gcs_uri_invalid_pattern():
    # Create mock storage client
    storage_mock = mock.AsyncMock()
    storage_mock.__aenter__ = mock.AsyncMock(return_value=storage_mock)
    storage_mock.__aexit__ = mock.AsyncMock()

    # Create mock storage factory
    mock_storage = mock.Mock()
    mock_storage.return_value = storage_mock

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up local storage dir
        os.environ["LOCAL_STORAGE_DIR"] = temp_dir

        # Inject the mock storage
        GCSSource.set_storage(mock_storage())

        document_search: DocumentSearch = DocumentSearch.from_config(CONFIG)

        # Test invalid patterns
        with pytest.raises(ValueError, match="GCSSource only supports '\\*' at the end of path"):
            await document_search.ingest("gcs://test-bucket/folder/**.txt")

        with pytest.raises(ValueError, match="GCSSource only supports '\\*' at the end of path"):
            await document_search.ingest("gcs://test-bucket/folder/test?.txt")

        with pytest.raises(ValueError, match="GCSSource only supports '\\*' at the end of path"):
            await document_search.ingest("gcs://test-bucket/folder/test*file.txt")

        # Test empty list response
        storage_mock.list_objects = mock.AsyncMock(return_value={"items": []})
        await document_search.ingest("gcs://test-bucket/folder/*")
        results = await document_search.search("GCS test content")
        assert len(results) == 0

        # Clean up
        storage_mock = mock.AsyncMock()
        storage_mock.download = mock.AsyncMock(return_value=b"")
        storage_mock.list_objects = mock.AsyncMock(return_value={"items": []})
        storage_mock.__aenter__ = mock.AsyncMock(return_value=storage_mock)
        storage_mock.__aexit__ = mock.AsyncMock()
        GCSSource.set_storage(storage_mock)
        del os.environ["LOCAL_STORAGE_DIR"]


@pytest.mark.asyncio
async def test_document_search_ingest_from_huggingface_uri_basic():
    # Create mock data
    mock_data = [
        {
            "content": "HuggingFace test content",
            "source": "dataset_name/train/test.txt",  # Must be .txt for TextDocument
        }
    ]

    # Create a simple dataset class that supports skip/take
    class MockDataset:
        def __init__(self, data: list):
            self.data = data
            self.current_index = 0

        def skip(self, n: int) -> "MockDataset":
            self.current_index = n
            return self

        def take(self, n: int) -> "MockDataset":
            return self

        def __iter__(self):
            if self.current_index < len(self.data):
                return iter(self.data[self.current_index : self.current_index + 1])
            return iter([])

    # Mock dataset loading and embeddings
    dataset = MockDataset(mock_data)
    embeddings_mock = AsyncMock()
    embeddings_mock.embed_text.return_value = [[0.1, 0.1]]  # Non-zero embeddings

    # Create parsers dict with actual provider instance
    parsers: Mapping[DocumentType, DocumentParser] = {DocumentType.TXT: TextDocumentParser()}

    # Mock vector store to track operations
    vector_store = InMemoryVectorStore(embedder=embeddings_mock)

    # Create a temporary directory for storing test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the environment variable for local storage
        os.environ["LOCAL_STORAGE_DIR"] = temp_dir
        storage_dir = Path(temp_dir)

        # Create the source directory and file
        source_dir = storage_dir / "dataset_name/train"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "test.txt"
        with open(source_file, mode="w", encoding="utf-8") as file:
            file.write("HuggingFace test content")

        with (
            mock.patch("ragbits.core.sources.hf.load_dataset", return_value=dataset),
            mock.patch("ragbits.core.sources.base.get_local_storage_dir", return_value=storage_dir),
        ):
            document_search: DocumentSearch = DocumentSearch(
                vector_store=vector_store,
                parser_router=DocumentParserRouter(parsers),
            )

            await document_search.ingest("hf://dataset_name/train/0")

            results = await document_search.search("HuggingFace test content")

            assert len(results) == 1
            assert isinstance(results[0], TextElement)
            assert results[0].content == "HuggingFace test content"
