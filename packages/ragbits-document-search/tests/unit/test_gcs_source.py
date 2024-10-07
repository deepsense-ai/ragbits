import os
from pathlib import Path

import aiohttp
import pytest

from ragbits.document_search.documents.sources import GCSSource

TEST_FILE_PATH = Path(__file__)

os.environ["LOCAL_STORAGE_DIR_ENV"] = TEST_FILE_PATH.parent.as_posix()


async def test_gcs_source_fetch():
    source = GCSSource(bucket="", object_name="test_gcs_source.py")

    path = await source.fetch()
    assert path == TEST_FILE_PATH

    source = GCSSource(bucket="", object_name="not_found_file.py")
    with pytest.raises(aiohttp.ClientConnectionError):
        await source.fetch()
