import os
from pathlib import Path

import pytest

from ragbits.document_search.documents.exceptions import SourceNotFoundError
from ragbits.document_search.documents.sources import LOCAL_STORAGE_DIR_ENV, HuggingFaceSource

from ..helpers import env_vars_not_set

os.environ[LOCAL_STORAGE_DIR_ENV] = Path(__file__).parent.as_posix()

HF_TOKEN_ENV = "HF_TOKEN"  # noqa: S105
HF_DATASET_PATH = "micpst/hf-docs"


@pytest.mark.skipif(
    env_vars_not_set([HF_TOKEN_ENV]),  # noqa: S105
    reason="Hugging Face environment variables not set",
)
async def test_huggingface_source_fetch() -> None:
    source = HuggingFaceSource(path=HF_DATASET_PATH, row=0)
    path = await source.fetch()

    assert path.is_file()
    assert path.name == "README.md"
    assert (
        path.read_text()
        == " `tokenizers-linux-x64-musl`\n\nThis is the **x86_64-unknown-linux-musl** binary for `tokenizers`\n"
    )

    path.unlink()


@pytest.mark.skipif(
    env_vars_not_set([HF_TOKEN_ENV]),
    reason="Hugging Face environment variables not set",
)
async def test_huggingface_source_fetch_not_found() -> None:
    source = HuggingFaceSource(path=HF_DATASET_PATH, row=1000)

    with pytest.raises(SourceNotFoundError) as exc:
        await source.fetch()

    assert str(exc.value) == "Source with ID huggingface:micpst/hf-docs/train/1000 not found."
