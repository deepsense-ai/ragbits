import uuid

import pytest

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore


@pytest.fixture(name="entries")
def entries_fixture() -> list[VectorStoreEntry]:
    entries = [
        VectorStoreEntry(id=uuid.uuid4(), text="foo"),
        VectorStoreEntry(id=uuid.uuid4(), text="bar"),
        VectorStoreEntry(id=uuid.uuid4(), text="baz"),
        VectorStoreEntry(id=uuid.uuid4(), text="qux"),
        VectorStoreEntry(id=uuid.uuid4(), text="quux"),
        VectorStoreEntry(id=uuid.uuid4(), text="corge"),
    ]
    entries.sort(key=lambda entry: entry.id)
    return entries


async def test_hybrid_store(entries: list[VectorStoreEntry]):
    vs1 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs2 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs_hybrid = HybridSearchVectorStore(vs1, vs2)

    await vs_hybrid.store(entries)
    vs1_entries = await vs1.list()
    vs2_entries = await vs2.list()
    vs1_entries.sort(key=lambda entry: entry.id)
    vs2_entries.sort(key=lambda entry: entry.id)

    assert vs1_entries == entries
    assert vs2_entries == entries


async def test_hybrid_list(entries: list[VectorStoreEntry]):
    vs1 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs2 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs_hybrid = HybridSearchVectorStore(vs1, vs2)

    await vs1.store(entries[:4])
    await vs2.store(entries[2:])
    vs_hybrid_entries = await vs_hybrid.list()
    vs_hybrid_entries.sort(key=lambda entry: entry.id)

    assert vs_hybrid_entries == entries


async def test_hybrid_list_limit(entries: list[VectorStoreEntry]):
    vs1 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs2 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs_hybrid = HybridSearchVectorStore(vs1, vs2)

    await vs1.store(entries[:4])
    await vs2.store(entries[2:])
    vs_hybrid_entries = await vs_hybrid.list(limit=3)
    vs_hybrid_entries.sort(key=lambda entry: entry.id)

    assert vs_hybrid_entries == entries[:3]


async def test_hybrid_list_limit_offset(entries: list[VectorStoreEntry]):
    vs1 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs2 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs_hybrid = HybridSearchVectorStore(vs1, vs2)

    await vs1.store(entries[:4])
    await vs2.store(entries[2:])
    vs_hybrid_entries = await vs_hybrid.list(limit=3, offset=2)
    vs_hybrid_entries.sort(key=lambda entry: entry.id)

    assert len(vs_hybrid_entries) == 3
    assert vs_hybrid_entries == entries[2:5]


async def test_hybrid_remove(entries: list[VectorStoreEntry]):
    vs1 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs2 = InMemoryVectorStore(embedder=NoopEmbedder())
    vs_hybrid = HybridSearchVectorStore(vs1, vs2)

    await vs1.store(entries)
    await vs2.store(entries)
    await vs_hybrid.remove([entries[2].id])

    vs1_entries = await vs1.list()
    vs2_entries = await vs2.list()
    vs1_entries.sort(key=lambda entry: entry.id)
    vs2_entries.sort(key=lambda entry: entry.id)

    assert vs1_entries == vs2_entries
    assert vs1_entries == entries[:2] + entries[3:]


async def test_hybrid_retrieve(entries: list[VectorStoreEntry]):
    vs1 = InMemoryVectorStore(
        embedder=NoopEmbedder(
            return_values=[
                [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]],  # for embedding
                [[2.1, 2.1]],  # for retrieval
            ],
        )
    )
    vs2 = InMemoryVectorStore(
        embedder=NoopEmbedder(
            return_values=[
                [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]],  # for embedding
                [[3.2, 3.2]],  # for retrieval
            ]
        )
    )
    vs_hybrid = HybridSearchVectorStore(vs1, vs2)

    await vs1.store(entries[:4])
    await vs2.store(entries[2:])

    results = await vs_hybrid.retrieve("foo")
    assert len(results) == len(entries)

    # indexes ordered by similarity score according to embeddings above
    entries_order = [2, 5, 3, 1, 4, 0]
    assert [r.entry for r in results] == [entries[i] for i in entries_order]
    assert [r.score for r in results] == [max(s.score for s in r.subresults) for r in results]
