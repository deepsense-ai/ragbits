from pathlib import Path
from uuid import UUID

import pytest
from chromadb import EphemeralClient
from qdrant_client import AsyncQdrantClient

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.sources import LocalFileSource

text_embbedings = [
    [[0.1, 0.2, 0.3], [0.9, 0.9, 0.9]],  # for storage
    [[0.12, 0.23, 0.29]],  # for retrieval
]

image_embbedings = [
    [[0.7, 0.8, 0.9], [1.0, 0.81, 0.84]],  # for storage
    [[0.99, 0.8, 0.85]],  # for retrieval
]

IMAGES_PATH = Path(__file__).parent.parent.parent / "test-images"


# TODO: Add PgVectorStore
@pytest.fixture(
    name="vector_store",
    params=[
        lambda: InMemoryVectorStore(
            embedder=NoopEmbedder(return_values=text_embbedings, image_return_values=image_embbedings),
        ),
        lambda: ChromaVectorStore(
            client=EphemeralClient(),
            index_name="test_index_name",
            embedder=NoopEmbedder(return_values=text_embbedings, image_return_values=image_embbedings),
        ),
        lambda: QdrantVectorStore(
            client=AsyncQdrantClient(":memory:"),
            index_name="test_index_name",
            embedder=NoopEmbedder(return_values=text_embbedings, image_return_values=image_embbedings),
        ),
    ],
    ids=["InMemoryVectorStore", "ChromaVectorStore", "QdrantVectorStore"],
)
def vector_store_fixture(request: pytest.FixtureRequest) -> VectorStore:
    return request.param()


@pytest.fixture(name="vector_store_entries")
def vector_store_entries_fixture() -> list[VectorStoreEntry]:
    with open(IMAGES_PATH / "test.png", "rb") as file:
        first_image_bytes = file.read()
    with open(IMAGES_PATH / "test2.jpg", "rb") as file:
        second_image_bytes = file.read()
    return [
        VectorStoreEntry(
            id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"),
            text="Text-only entry",
            metadata={"foo": "bar", "nested_foo": {"nested_bar": "nested_baz"}, "some_list": [1, 2, 3]},
        ),
        VectorStoreEntry(
            id=UUID("367cd073-6a6b-47fe-a032-4bb3a754f6fe"),
            image_bytes=first_image_bytes,
        ),
        VectorStoreEntry(
            id=UUID("d9d11902-f26a-409b-967b-46c30f0b65de"),
            image_bytes=second_image_bytes,
            text="Text and image entry",
            metadata={"baz": "qux"},
        ),
    ]


async def test_vector_store_list(
    vector_store: VectorStore,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    result_entries = await vector_store.list()

    sorted_results = sorted(result_entries, key=lambda entry: entry.id)
    sorted_expected = sorted(vector_store_entries, key=lambda entry: entry.id)

    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.id == expected.id

        # Chroma is unable to store None values so unfortunately we have to tolerate empty strings
        assert result.text == expected.text or (expected.text is None and result.text == "")
        assert result.metadata == expected.metadata
        assert result.image_bytes == expected.image_bytes


async def test_vector_store_remove(
    vector_store: VectorStore,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    await vector_store.remove([vector_store_entries[2].id])

    result_entries = await vector_store.list()
    assert len(result_entries) == 2
    assert vector_store_entries[2].id not in {entry.id for entry in result_entries}


async def test_vector_store_retrieve(
    vector_store: VectorStore,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    result_entries = await vector_store.retrieve(text="foo")

    sorted_results = sorted(result_entries, key=lambda r: r.entry.id)
    sorted_expected = sorted(vector_store_entries, key=lambda entry: entry.id)

    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.entry.id == expected.id
        assert result.score != 0

        # Chroma is unable to store None values so unfortunately we have to tolerate empty strings
        assert result.entry.text == expected.text or (expected.text is None and result.entry.text == "")
        assert result.entry.metadata == expected.metadata
        assert result.entry.image_bytes == expected.image_bytes


async def test_vector_store_retrieve_by_text(
    vector_store: VectorStore,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    results = await vector_store.retrieve(text="foo", options=VectorStoreOptions(k=2))

    assert len(results) == 2
    assert results[0].entry.id == vector_store_entries[0].id
    assert results[1].entry.id == vector_store_entries[1].id


async def test_vector_store_retrieve_by_image(
    vector_store: VectorStore,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    results = await vector_store.retrieve(image=vector_store_entries[1].image_bytes, options=VectorStoreOptions(k=2))

    assert len(results) == 2
    assert results[0].entry.id == vector_store_entries[2].id
    assert results[1].entry.id == vector_store_entries[1].id


async def test_handling_document_ingestion_with_different_content_and_verifying_replacement(
    vector_store: VectorStore,
) -> None:
    document_1_content = "This is a test sentence and it should be in the vector store"
    document_2_content = "This is another test sentence and it should be removed from the vector store"
    document_2_new_content = "This is one more test sentence and it should be added to the vector store"

    document_1 = DocumentMeta.create_text_document_from_literal(document_1_content)
    document_2 = DocumentMeta.create_text_document_from_literal(document_2_content)

    document_search = DocumentSearch(
        vector_store=vector_store,
    )
    await document_search.ingest([document_1, document_2])

    if isinstance(document_2.source, LocalFileSource):
        document_2_path = document_2.source.path
    with open(document_2_path, "w") as file:
        file.write(document_2_new_content)

    await document_search.ingest([document_2])

    document_contents = {entry.text for entry in await vector_store.list()}

    assert document_1_content in document_contents
    assert document_2_new_content in document_contents
    assert document_2_content not in document_contents
