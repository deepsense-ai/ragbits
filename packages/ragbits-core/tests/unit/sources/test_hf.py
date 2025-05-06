from unittest.mock import MagicMock, patch

from ragbits.core.sources.hf import HuggingFaceSource


async def test_huggingface_source_fetch() -> None:
    take = MagicMock(return_value=[{"content": "This is the content of the file.", "source": "doc.md"}])
    skip = MagicMock(return_value=MagicMock(take=take))
    data = MagicMock(skip=skip)
    source = HuggingFaceSource(path="org/docs", split="train", row=1)

    with patch("ragbits.core.sources.hf.load_dataset", return_value=data):
        path = await source.fetch()

    assert source.id == "hf:org/docs/train/1"
    assert path.name == "doc.md"
    assert path.read_text() == "This is the content of the file."
