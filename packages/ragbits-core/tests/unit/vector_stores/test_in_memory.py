from pathlib import Path

import pytest
from pydantic import computed_field

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.sources.local import LocalFileSource
from ragbits.core.vector_stores.base import EmbeddingType, VectorStoreOptions
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element


class AnimalElement(Element):
    """
    A test element representing an animal.
    """

    element_type: str = "animal"
    name: str
    species: str | None
    type: str
    age: int
    photo: bytes | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_representation(self) -> str | None:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """
        return self.species

    @property
    def image_representation(self) -> bytes | None:
        """
        Get the image representation of the element.

        Returns:
            The image representation.
        """
        return self.photo


async def text_store_fixture() -> InMemoryVectorStore:
    def meta(name: str) -> DocumentMeta:
        return DocumentMeta(document_type=DocumentType.TXT, source=LocalFileSource(path=Path(f"{name}.txt")))

    elements = [
        (
            AnimalElement(name="spikey", species="dog", type="mammal", age=5, document_meta=meta("spikey")),
            [0.5, 0.5],
        ),
        (
            AnimalElement(name="fluffy", species="cat", type="mammal", age=3, document_meta=meta("fluffy")),
            [0.6, 0.6],
        ),
        (
            AnimalElement(name="slimy", species="frog", type="amphibian", age=1, document_meta=meta("slimey")),
            [0.7, 0.7],
        ),
        (
            AnimalElement(name="scaly", species="snake", type="reptile", age=2, document_meta=meta("scaly")),
            [0.8, 0.8],
        ),
        (
            AnimalElement(name="hairy", species="spider", type="insect", age=6, document_meta=meta("hairy")),
            [0.9, 0.9],
        ),
        (
            AnimalElement(
                name="spotty", species="ladybug", type="insect", age=1, photo=b"image", document_meta=meta("spotty")
            ),
            [0.1, 0.1],
        ),
        (
            AnimalElement(  # Image-only element, should be ignored by text-only store
                name="photty", species=None, type="insect", age=6, document_meta=meta("photty.jpg"), photo=b"image"
            ),
            [0.2, 0.2],
        ),
    ]

    entries = [element[0].to_vector_db_entry() for element in elements]

    embeddings = [element[1] for element in elements]
    search_vector = [0.4, 0.4]

    store = InMemoryVectorStore(embedder=NoopEmbedder(return_values=[embeddings, [search_vector]]))
    await store.store(entries)
    return store


async def image_store_fixture() -> InMemoryVectorStore:
    def meta(name: str) -> DocumentMeta:
        return DocumentMeta(document_type=DocumentType.JPG, source=LocalFileSource(path=Path(f"{name}.jpg")))

    elements = [
        (
            AnimalElement(
                name="spikey", species="dog", type="mammal", age=5, photo=b"image", document_meta=meta("spikey")
            ),
            [0.5, 0.5],
        ),
        (
            AnimalElement(
                name="fluffy", species="cat", type="mammal", age=3, photo=b"image", document_meta=meta("fluffy")
            ),
            [0.6, 0.6],
        ),
        (
            AnimalElement(
                name="slimy", species=None, type="amphibian", age=1, photo=b"image", document_meta=meta("slimey")
            ),
            [0.7, 0.7],
        ),
        (
            AnimalElement(
                name="scaly", species=None, type="reptile", age=2, photo=b"image", document_meta=meta("scaly")
            ),
            [0.8, 0.8],
        ),
        (
            AnimalElement(
                name="hairy", species="spider", type="insect", age=6, photo=b"image", document_meta=meta("hairy")
            ),
            [0.9, 0.9],
        ),
        (
            AnimalElement(
                name="spotty", species=None, type="insect", age=1, photo=b"image", document_meta=meta("spotty")
            ),
            [0.1, 0.1],
        ),
        (
            AnimalElement(  # Text-only element, should be ignored by image-only store
                name="texty",
                species="spider",
                type="insect",
                age=6,
                document_meta=meta("texty"),
            ),
            [0.2, 0.2],
        ),
    ]

    entries = [element[0].to_vector_db_entry() for element in elements]

    embeddings = [element[1] for element in elements]
    search_vector = [0.4, 0.4]

    store = InMemoryVectorStore(
        embedder=NoopEmbedder(return_values=[[search_vector]], image_return_values=[embeddings]),
        embedding_type=EmbeddingType.IMAGE,
    )
    await store.store(entries)
    return store


@pytest.fixture(
    name="store",
    params=[
        text_store_fixture,
        image_store_fixture,
    ],
    ids=["text store", "image store"],
)
async def vector_store_fixture(request: pytest.FixtureRequest) -> InMemoryVectorStore:
    return await request.param()


@pytest.mark.parametrize(
    ("k", "score_threshold", "results"),
    [
        (5, None, ["spikey", "fluffy", "slimy", "spotty", "scaly"]),
        (2, None, ["spikey", "fluffy"]),
        (5, -0.3, ["spikey", "fluffy"]),
    ],
)
async def test_retrieve(store: InMemoryVectorStore, k: int, score_threshold: float | None, results: list[str]) -> None:
    query_results = await store.retrieve("query", options=VectorStoreOptions(k=k, score_threshold=score_threshold))

    assert len(query_results) == len(results)
    for query_result, result in zip(query_results, results, strict=True):
        assert query_result.entry.metadata["name"] == result


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
