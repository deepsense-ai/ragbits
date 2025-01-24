from pathlib import Path

import pytest
from pydantic import computed_field

from ragbits.core.embeddings import EmbeddingType
from ragbits.core.vector_stores.base import VectorStoreOptions, VectorStoreEntry
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import LocalFileSource


class AnimalElement(Element):
    """
    A test element representing an animal.
    """

    element_type: str = "animal"
    name: str
    species: str
    type: str
    age: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_representation(self) -> str:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """
        return self.name


@pytest.fixture(name="store")
async def store_fixture() -> InMemoryVectorStore:
    document_meta = DocumentMeta(document_type=DocumentType.TXT, source=LocalFileSource(path=Path("test.txt")))
    elements = [
        (AnimalElement(name="spikey", species="dog", type="mammal", age=5, document_meta=document_meta), [0.5, 0.5]),
        (AnimalElement(name="fluffy", species="cat", type="mammal", age=3, document_meta=document_meta), [0.6, 0.6]),
        (AnimalElement(name="slimy", species="frog", type="amphibian", age=1, document_meta=document_meta), [0.7, 0.7]),
        (AnimalElement(name="scaly", species="snake", type="reptile", age=2, document_meta=document_meta), [0.8, 0.8]),
        (AnimalElement(name="hairy", species="spider", type="insect", age=6, document_meta=document_meta), [0.9, 0.9]),
        (
            AnimalElement(name="spotty", species="ladybug", type="insect", age=1, document_meta=document_meta),
            [0.1, 0.1],
        ),
    ]

    entries = [
        element[0].to_vector_db_entry(vector=element[1], embedding_type=EmbeddingType.TEXT) for element in elements
    ]

    store = InMemoryVectorStore()
    await store.store(entries)
    return store


@pytest.fixture
def vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture
def entries() -> list[VectorStoreEntry]:
    return [
        VectorStoreEntry(
            id="1",
            key="test1",
            text="test1",
            metadata={"embedding_type": "text", "vector": [1.0, 0.0]},
        ),
        VectorStoreEntry(
            id="2",
            key="test2",
            text="test2",
            metadata={"embedding_type": "text", "vector": [0.0, 1.0]},
        ),
    ]


async def test_store_and_retrieve(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0])
    assert len(results) == 2
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 0.0
    assert results[1].entry.id == "2"
    assert results[1].entry.key == "test2"
    assert results[1].vectors["text"] == [0.0, 1.0]
    assert results[1].score == pytest.approx(1.4142135623730951)


async def test_store_and_retrieve_with_max_distance(
    vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]
) -> None:
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0], options=vector_store.options_cls(max_distance=1.0))
    assert len(results) == 1
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 0.0


async def test_store_and_retrieve_with_k(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.retrieve([1.0, 0.0], options=vector_store.options_cls(k=1))
    assert len(results) == 1
    assert results[0].entry.id == "1"
    assert results[0].entry.key == "test1"
    assert results[0].vectors["text"] == [1.0, 0.0]
    assert results[0].score == 0.0


async def test_store_and_list(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list()
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[0].key == "test1"
    assert results[1].id == "2"
    assert results[1].key == "test2"


async def test_store_and_list_with_limit(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list(limit=1)
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].key == "test1"


async def test_store_and_list_with_offset(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list(offset=1)
    assert len(results) == 1
    assert results[0].id == "2"
    assert results[0].key == "test2"


async def test_store_and_list_with_where(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    results = await vector_store.list(where={"embedding_type": "text"})
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[0].key == "test1"
    assert results[1].id == "2"
    assert results[1].key == "test2"


async def test_store_and_remove(vector_store: InMemoryVectorStore, entries: list[VectorStoreEntry]) -> None:
    await vector_store.store(entries)
    await vector_store.remove(["1"])
    results = await vector_store.list()
    assert len(results) == 1
    assert results[0].id == "2"
    assert results[0].key == "test2"


@pytest.mark.parametrize(
    ("k", "max_distance", "results"),
    [
        (5, None, ["spikey", "fluffy", "slimy", "spotty", "scaly"]),
        (2, None, ["spikey", "fluffy"]),
        (5, 0.3, ["spikey", "fluffy"]),
    ],
)
async def test_retrieve(store: InMemoryVectorStore, k: int, max_distance: float | None, results: list[str]) -> None:
    search_vector = [0.4, 0.4]

    entries = await store.retrieve(search_vector, options=VectorStoreOptions(k=k, max_distance=max_distance))

    assert len(entries) == len(results)
    for entry, result in zip(entries, results, strict=True):
        assert entry.metadata["name"] == result


async def test_remove(store: InMemoryVectorStore) -> None:
    entries = await store.list()
    entry_number = len(entries)

    ids_to_remove = [entries[0].id]
    await store.remove(ids_to_remove)

    assert len(await store.list()) == entry_number - 1


async def test_list_all(store: InMemoryVectorStore) -> None:
    results = await store.list()

    assert len(results) == 6
    names = [result.metadata["name"] for result in results]
    assert names == ["spikey", "fluffy", "slimy", "scaly", "hairy", "spotty"]


async def test_list_limit(store: InMemoryVectorStore) -> None:
    results = await store.list(limit=3)

    assert len(results) == 3
    names = {result.metadata["name"] for result in results}
    assert names == {"spikey", "fluffy", "slimy"}


async def test_list_offset(store: InMemoryVectorStore) -> None:
    results = await store.list(offset=3)

    assert len(results) == 3
    names = {result.metadata["name"] for result in results}
    assert names == {"scaly", "hairy", "spotty"}


async def test_limit_with_offset(store: InMemoryVectorStore) -> None:
    results = await store.list(limit=2, offset=3)

    assert len(results) == 2
    names = {result.metadata["name"] for result in results}
    assert names == {"scaly", "hairy"}


async def test_where(store: InMemoryVectorStore) -> None:
    results = await store.list(where={"type": "insect"})

    assert len(results) == 2
    names = {result.metadata["name"] for result in results}
    assert names == {"hairy", "spotty"}


async def test_multiple_where(store: InMemoryVectorStore) -> None:
    results = await store.list(where={"type": "insect", "age": 1})

    assert len(results) == 1
    assert results[0].metadata["name"] == "spotty"


async def test_empty_where(store: InMemoryVectorStore) -> None:
    results = await store.list(where={})

    assert len(results) == 6
    names = {result.metadata["name"] for result in results}
    assert names == {"spikey", "fluffy", "slimy", "scaly", "hairy", "spotty"}


async def test_empty_results(store: InMemoryVectorStore) -> None:
    results = await store.list(where={"type": "bird"})

    assert len(results) == 0


async def test_empty_results_with_limit(store: InMemoryVectorStore) -> None:
    results = await store.list(where={"type": "bird"}, limit=2)

    assert len(results) == 0


async def test_where_limit(store: InMemoryVectorStore) -> None:
    results = await store.list(where={"type": "insect"}, limit=1)

    assert len(results) == 1
    assert results[0].metadata["name"] == "hairy"
