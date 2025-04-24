from functools import partial

import pytest
from qdrant_client import AsyncQdrantClient

from ragbits.core.embeddings.sparse import BagOfTokens
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreWithSparseDenseEmbedder,
)
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore

from .test_vector_store import vector_store_entries_fixture  # noqa: F401


@pytest.fixture(
    name="vector_store_cls",
    params=[
        lambda: partial(InMemoryVectorStore),
        lambda: partial(QdrantVectorStore, client=AsyncQdrantClient(":memory:"), index_name="test_index_name"),
    ],
    ids=["InMemoryVectorStore", "QdrantVectorStore"],
)
def vector_store_cls_fixture(request: pytest.FixtureRequest) -> type[VectorStoreWithSparseDenseEmbedder]:
    """
    Returns vector stores classes with different backends, with backend-specific parameters already set,
    but parameters common to VectorStoreWithSparseDenseEmbedder left to be set.
    """
    return request.param()


@pytest.fixture(name="vector_store")
def vector_store_fixture(
    vector_store_cls: type[VectorStoreWithSparseDenseEmbedder],
) -> VectorStoreWithSparseDenseEmbedder:
    """
    For each vector store in `vector_store_cls`, returns an instance with sparse embedder for text embeddings
    """
    return vector_store_cls(embedder=BagOfTokens())


async def test_vector_store_list(
    vector_store: VectorStoreWithSparseDenseEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    result_entries = await vector_store.list()
    expected_entries = (
        [e for e in vector_store_entries if e.text is not None]
        if vector_store._embedding_type == EmbeddingType.TEXT
        else [e for e in vector_store_entries if e.image_bytes is not None]
    )

    sorted_results = sorted(result_entries, key=lambda entry: entry.id)
    sorted_expected = sorted(expected_entries, key=lambda entry: entry.id)

    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.id == expected.id

        # Chroma is unable to store None values so unfortunately we have to tolerate empty strings
        assert result.text == expected.text or (expected.text is None and result.text == "")
        assert result.metadata == expected.metadata
        assert result.image_bytes == expected.image_bytes


async def test_vector_store_remove(
    vector_store: VectorStoreWithSparseDenseEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    await vector_store.remove([vector_store_entries[2].id])

    result_entries = await vector_store.list()
    assert len(result_entries) == 1
    assert vector_store_entries[2].id not in {entry.id for entry in result_entries}


async def test_vector_store_retrieve(
    vector_store: VectorStoreWithSparseDenseEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    result_entries = await vector_store.retrieve(text="entry consisting only of text")
    expected_entries = (
        [e for e in vector_store_entries if e.text is not None]
        if vector_store._embedding_type == EmbeddingType.TEXT
        else [e for e in vector_store_entries if e.image_bytes is not None]
    )

    sorted_results = sorted(result_entries, key=lambda r: r.entry.id)
    sorted_expected = sorted(expected_entries, key=lambda entry: entry.id)

    prev_score = float("inf")
    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.entry.id == expected.id
        print(result.score, result.entry.text, result.vector)
        # assert result.score != 0
        assert result.score <= prev_score  # Ensure that the results are sorted by score and bigger is better
        prev_score = result.score

        assert result.entry.text == expected.text
        assert result.entry.metadata == expected.metadata
        assert result.entry.image_bytes == expected.image_bytes


async def test_vector_store_retrieve_order(
    vector_store: VectorStoreWithSparseDenseEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)

    results = await vector_store.retrieve(text="entry consisting only of text", options=VectorStoreOptions(k=1))
    assert len(results) == 1
    expected_entry = vector_store_entries[0]
    assert results[0].entry.id == expected_entry.id

    results = await vector_store.retrieve(text="entry containing text and image", options=VectorStoreOptions(k=1))
    assert len(results) == 1
    expected_entry = vector_store_entries[2]
    assert results[0].entry.id == expected_entry.id
