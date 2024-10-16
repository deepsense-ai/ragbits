import os
from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest

from ragbits.document_search.documents.sources import LOCAL_STORAGE_DIR_ENV, GCSSource, HuggingFaceSource

TEST_FILE_PATH = Path(__file__)

os.environ[LOCAL_STORAGE_DIR_ENV] = TEST_FILE_PATH.parent.as_posix()


async def test_gcs_source_fetch() -> None:
    source = GCSSource(bucket="", object_name="test_gcs_source.py")
    assert source.id == "gcs:gs:///test_gcs_source.py"

    path = await source.fetch()
    assert path == TEST_FILE_PATH

    source = GCSSource(bucket="", object_name="not_found_file.py")
    assert source.id == "gcs:gs:///not_found_file.py"

    with pytest.raises(aiohttp.ClientConnectionError):
        await source.fetch()


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
