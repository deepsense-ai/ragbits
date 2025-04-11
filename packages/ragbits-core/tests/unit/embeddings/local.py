import pickle

import numpy as np
import pytest

from ragbits.core.embeddings.local import LocalEmbedder, LocalEmbedderOptions


@pytest.mark.asyncio
async def test_local_embedder_embed_text():
    embedder = LocalEmbedder("sentence-transformers/all-MiniLM-L6-v2")

    result = await embedder.embed_text(["test text"])

    # Check that embeddings have the expected shape
    assert len(result) == 1
    assert len(result[0]) == 384  # This dimension depends on the model


@pytest.mark.asyncio
async def test_local_embedder_with_custom_encode_kwargs():
    # Test with custom encode parameters
    options = LocalEmbedderOptions(
        encode_kwargs={"prompt": "Represent this sentence for searching relevant passages: "}
    )
    embedder = LocalEmbedder("BAAI/bge-small-en-v1.5", default_options=options)
    result = await embedder.embed_text(["test text"])

    assert len(result) == 1
    assert len(result[0]) > 0

    embedder = LocalEmbedder("BAAI/bge-small-en-v1.5")
    result_no_prompt = await embedder.embed_text(["test text"])

    assert not np.array_equal(result[0], result_no_prompt[0])


def test_local_embedder_pickling():
    embedder = LocalEmbedder("sentence-transformers/all-MiniLM-L6-v2")
    pickled = pickle.dumps(embedder)
    unpickled = pickle.loads(pickled)  # noqa: S301

    assert isinstance(unpickled, LocalEmbedder)
    assert unpickled.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert unpickled.default_options == embedder.default_options
