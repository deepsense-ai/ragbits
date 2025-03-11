from ragbits.core.embeddings.fastembed import FastEmbedEmbedder, FastEmbedSparseEmbedder


async def test_fastembed_dense_embeddings():
    embeddings = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")
    result = await embeddings.embed_text(["text1"])
    assert len(result[0]) == 384


async def test_fastembed_sparse_embeddings():
    embeddings = FastEmbedSparseEmbedder("qdrant/bm25")
    result = await embeddings.embed_text(["text1"])
    assert len(result[0].values) == len(result[0].indices)
