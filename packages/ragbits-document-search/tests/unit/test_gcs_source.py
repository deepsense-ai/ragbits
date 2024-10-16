import os
from pathlib import Path

from ragbits.document_search.documents.sources import GCSSource

TEST_FILE_PATH = Path(__file__)

os.environ["LOCAL_STORAGE_DIR_ENV"] = TEST_FILE_PATH.parent.as_posix()


async def test_gcs_source_fetch():
    source = GCSSource(bucket="", object_name="test_gcs_source.py")

    path = await source.fetch()
    assert path == TEST_FILE_PATH
