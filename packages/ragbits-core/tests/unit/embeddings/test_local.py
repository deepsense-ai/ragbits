import pickle

import numpy as np

from ragbits.core.embeddings.dense.local import LocalEmbedder, LocalEmbedderOptions


async def test_local_embedder_embed_text():
    embedder = LocalEmbedder("sentence-transformers/all-MiniLM-L6-v2")

    result = await embedder.embed_text(["test text"])

    # Check that embeddings have the expected shape
    assert len(result) == 1
    assert len(result[0]) == 384  # This dimension depends on the model


async def test_local_embedder_with_custom_encode_kwargs():
    # Test with custom encode parameters
    embedder = LocalEmbedder(
        "BAAI/bge-small-en-v1.5",
        prompts={
            "classification": "Classify the following text: ",
            "retrieval": "Retrieve semantically similar text: ",
            "clustering": "Identify the topic or theme based on the text: ",
        },
    )
    options = LocalEmbedderOptions(encode_kwargs={"prompt_name": "retrieval"})
    result = await embedder.embed_text(["test text"], options=options)

    assert len(result) == 1
    assert len(result[0]) > 0

    embedder = LocalEmbedder("BAAI/bge-small-en-v1.5")
    result_no_prompt = await embedder.embed_text(["test text"])

    # Check that the embeddings with custom prompt are different from the default ones
    assert not np.array_equal(result[0], result_no_prompt[0])


def test_local_embedder_pickling():
    embedder = LocalEmbedder("sentence-transformers/all-MiniLM-L6-v2")
    pickled = pickle.dumps(embedder)
    unpickled = pickle.loads(pickled)  # noqa: S301

    assert isinstance(unpickled, LocalEmbedder)
    assert unpickled.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert unpickled.default_options == embedder.default_options
