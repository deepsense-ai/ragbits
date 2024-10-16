from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from ragbits.document_search.documents.sources import HuggingFaceSource

from ..helpers import env_vars_not_set

HF_TOKEN_ENV = "HF_TOKEN"  # nosec
HF_DATASET_PATH = "micpst/hf-docs?row=0"


@pytest.fixture
async def fetch_huggingface_source() -> AsyncGenerator[Path]:
    source = HuggingFaceSource(hf_path=HF_DATASET_PATH)
    path = await source.fetch()
    yield path
    path.unlink()


@pytest.mark.skipif(
    env_vars_not_set([HF_TOKEN_ENV]),
    reason="Hugging Face environment variables not set",
)
async def test_huggingface_source_fetch(fetch_huggingface_source: Path) -> None:
    path = fetch_huggingface_source

    assert path.is_file()
    assert path.name == "README.md"
    assert (
        path.read_text()
        == " `tokenizers-linux-x64-musl`\n\nThis is the **x86_64-unknown-linux-musl** binary for `tokenizers`\n"
    )
