import os
import shutil
import tempfile
from pathlib import Path

import pytest

from ragbits.core.sources.base import LOCAL_STORAGE_DIR_ENV


@pytest.fixture(scope="module", autouse=True)
def configure_local_storage_dir():
    random_tmp_dir = Path(tempfile.mkdtemp())
    os.environ[LOCAL_STORAGE_DIR_ENV] = random_tmp_dir.as_posix()
    yield
    shutil.rmtree(random_tmp_dir)
