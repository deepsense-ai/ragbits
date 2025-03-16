import pickle

from ragbits.core.embeddings.fastembed import FastEmbedEmbedder, FastEmbedSparseEmbedder


async def test_fastembed_dense_embeddings():
    embeddings = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")
    result = await embeddings.embed_text(["text1"])
    assert len(result[0]) == 384


async def test_fastembed_sparse_embeddings():
    embeddings = FastEmbedSparseEmbedder("qdrant/bm25")
    result = await embeddings.embed_text(["text1"])
    assert len(result[0].values) == len(result[0].indices)


def test_fastembed_dense_pickling():
    embeddings = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")
    pickled = pickle.dumps(embeddings)
    unpickled = pickle.loads(pickled)  # noqa: S301
    assert isinstance(unpickled, FastEmbedEmbedder)
    assert unpickled.model_name == "BAAI/bge-small-en-v1.5"
    assert unpickled.default_options == embeddings.default_options
    assert unpickled.use_gpu == embeddings.use_gpu


def test_fastembed_sparse_pickling():
    embeddings = FastEmbedSparseEmbedder("qdrant/bm25")
    pickled = pickle.dumps(embeddings)
    unpickled = pickle.loads(pickled)  # noqa: S301
    assert isinstance(unpickled, FastEmbedSparseEmbedder)
    assert unpickled.model_name == "qdrant/bm25"
    assert unpickled.default_options == embeddings.default_options
    assert unpickled.use_gpu == embeddings.use_gpu
