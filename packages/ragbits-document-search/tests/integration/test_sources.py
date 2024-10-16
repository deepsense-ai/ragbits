import os
from pathlib import Path

import pytest

from ragbits.document_search.documents.sources import LOCAL_STORAGE_DIR_ENV, HuggingFaceSource

from ..helpers import env_vars_not_set

os.environ[LOCAL_STORAGE_DIR_ENV] = Path(__file__).parent.as_posix()

HF_TOKEN_ENV = "HF_TOKEN"  # nosec
HF_DATASET_PATH = "micpst/hf-docs?row=0"


@pytest.mark.skipif(
    env_vars_not_set([HF_TOKEN_ENV]),
    reason="Hugging Face environment variables not set",
)
async def test_huggingface_source_fetch() -> None:
    source = HuggingFaceSource(hf_path=HF_DATASET_PATH)
    path = await source.fetch()

    assert path.is_file()
    assert path.name == "README.md"
    assert (
        path.read_text()
        == " `tokenizers-linux-x64-musl`\n\nThis is the **x86_64-unknown-linux-musl** binary for `tokenizers`\n"
    )

    path.unlink()
