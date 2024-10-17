from pathlib import Path

from ragbits.document_search.documents.sources import LocalFileSource

TEST_FILE_PATH = Path(__file__)


async def test_local_source_fetch():
    source = LocalFileSource(path=TEST_FILE_PATH)

    path = await source.fetch()

    assert path == TEST_FILE_PATH


async def test_local_source_list_sources():
    example_files = TEST_FILE_PATH.parent / "example_files"

    sources = LocalFileSource.list_sources(example_files, file_pattern="*.md")

    assert len(sources) == 2
    assert all(isinstance(source, LocalFileSource) for source in sources)
    assert all(source.path.suffix == ".md" for source in sources)
