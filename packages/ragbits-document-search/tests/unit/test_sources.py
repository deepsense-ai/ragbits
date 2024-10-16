import os
from pathlib import Path
from unittest.mock import patch

from ragbits.document_search.documents.sources import LOCAL_STORAGE_DIR_ENV, GCSSource, HuggingFaceSource

os.environ[LOCAL_STORAGE_DIR_ENV] = Path(__file__).parent.as_posix()


async def test_gcs_source_fetch() -> None:
    data = b"This is the content of the file."
    source = GCSSource(bucket="", object_name="doc.md")

    with patch("ragbits.document_search.documents.sources.Storage.download", return_value=data):
        path = await source.fetch()

    assert source.id == "gcs:gs:///doc.md"
    assert path.name == "doc.md"
    assert path.read_text() == "This is the content of the file."

    path.unlink()


async def test_huggingface_source_fetch() -> None:
    dataset = [
        {"content": "This is the first document.", "source": "first_document.txt"},
        {"content": "This is the second document.", "source": "second_document.txt"},
        {"content": "This is the third document.", "source": "third_document.txt"},
    ]
    source = HuggingFaceSource(hf_path="org/docs?row=1")

    with patch("ragbits.document_search.documents.sources.load_dataset", return_value=dataset):
        path = await source.fetch()

    assert source.id == "huggingface:org/docs?row=1"
    assert path.name == "second_document.txt"
    assert path.read_text() == "This is the second document."

    path.unlink()
