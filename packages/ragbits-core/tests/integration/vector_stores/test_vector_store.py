from functools import partial
from pathlib import Path
from typing import cast
from uuid import UUID

import asyncpg
import pytest
from chromadb import EphemeralClient
from psycopg import Connection
from qdrant_client import AsyncQdrantClient

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.sources.local import LocalFileSource
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStore,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreWithExternalEmbedder,
)
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.pgvector import PgVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

text_embbedings = [
    [[0.1, 0.2, 0.3], [0.9, 0.9, 0.9]],  # for storage
    [[0.12, 0.23, 0.29]],  # for retrieval
]

image_embeddings = [
    [[0.7, 0.8, 0.9], [1.0, 0.81, 0.84]],
]

IMAGES_PATH = Path(__file__).parent.parent.parent / "assets" / "img"


@pytest.fixture
async def pgvector_test_db(postgresql: Connection) -> asyncpg.pool:
    dsn = f"postgresql://{postgresql.info.user}:{postgresql.info.password}@{postgresql.info.host}:{postgresql.info.port}/{postgresql.info.dbname}"
    async with asyncpg.create_pool(dsn) as pool:
        yield pool


@pytest.fixture(
    name="vector_store_cls",
    params=[
        lambda _: partial(InMemoryVectorStore),
        lambda _: partial(ChromaVectorStore, client=EphemeralClient(), index_name="test_index_name"),
        lambda _: partial(QdrantVectorStore, client=AsyncQdrantClient(":memory:"), index_name="test_index_name"),
        lambda pg_pool: partial(PgVectorStore, client=pg_pool, table_name="test_index_name", vector_size=3),
    ],
    ids=["InMemoryVectorStore", "ChromaVectorStore", "QdrantVectorStore", "PgVectorStore"],
)
def vector_store_cls_fixture(
    request: pytest.FixtureRequest, pgvector_test_db: asyncpg.pool
) -> type[VectorStoreWithExternalEmbedder]:
    """
    Returns vector stores classes with different backends, with backend-specific parameters already set,
    but parameters common to VectorStoreWithExternalEmbedder left to be set.
    """
    return request.param(pgvector_test_db)


@pytest.fixture(name="vector_store", params=[EmbeddingType.TEXT, EmbeddingType.IMAGE], ids=["Text", "Image"])
def vector_store_fixture(
    vector_store_cls: type[VectorStoreWithExternalEmbedder],
    request: pytest.FixtureRequest,
) -> VectorStoreWithExternalEmbedder:
    """
    For each vector store in `vector_store_cls`, returns two instances of it, one for text and one for image embeddings.
    """
    embedder = (
        NoopEmbedder(return_values=text_embbedings)
        if request.param == EmbeddingType.TEXT
        else NoopEmbedder(return_values=text_embbedings[-1:], image_return_values=image_embeddings)
    )

    # Workaround for Chroma reusing resources between EphemeralClient() instances
    partial_cls = cast(partial, vector_store_cls)
    if "index_name" in partial_cls.keywords:
        partial_cls.keywords["index_name"] = f"{partial_cls.keywords['index_name']}_{request.param.name.lower()}"

    return vector_store_cls(embedder=embedder, embedding_type=request.param)


@pytest.fixture(name="text_vector_store")
def text_vector_store_fixture(
    vector_store_cls: type[VectorStoreWithExternalEmbedder],
) -> VectorStoreWithExternalEmbedder:
    """
    For each vector store in `vector_store_cls`, returns an instance of it for text embeddings.
    """
    embedder = NoopEmbedder(return_values=text_embbedings)
    return vector_store_cls(embedder=embedder, embedding_type=EmbeddingType.TEXT)


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
    vector_store: VectorStoreWithExternalEmbedder,
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
    vector_store: VectorStoreWithExternalEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    await vector_store.remove([vector_store_entries[2].id])

    result_entries = await vector_store.list()
    assert len(result_entries) == 1
    assert vector_store_entries[2].id not in {entry.id for entry in result_entries}


async def test_vector_store_retrieve(
    vector_store: VectorStoreWithExternalEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    result_entries = await vector_store.retrieve(text="foo")
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
        assert result.score != 0
        assert result.score <= prev_score  # Ensure that the results are sorted by score and bigger is better
        prev_score = result.score

        # Chroma is unable to store None values so unfortunately we have to tolerate empty strings
        assert result.entry.text == expected.text or (expected.text is None and result.entry.text == "")
        assert result.entry.metadata == expected.metadata
        assert result.entry.image_bytes == expected.image_bytes


async def test_vector_store_retrieve_order(
    vector_store: VectorStoreWithExternalEmbedder,
    vector_store_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_entries)
    results = await vector_store.retrieve(text="foo", options=VectorStoreOptions(k=1))

    assert len(results) == 1
    expected_entry = (
        vector_store_entries[0] if vector_store._embedding_type == EmbeddingType.TEXT else vector_store_entries[1]
    )

    assert results[0].entry.id == expected_entry.id


def test_image_store_with_non_image_embedder(vector_store_cls: type[VectorStoreWithExternalEmbedder]) -> None:
    # When an image vector store is created with a text-only embedder, it should raise a ValueError
    with pytest.raises(ValueError):
        vector_store_cls(embedder=NoopEmbedder(return_values=text_embbedings), embedding_type=EmbeddingType.IMAGE)


async def test_handling_document_ingestion_with_different_content_and_verifying_replacement(
    text_vector_store: VectorStore,
) -> None:
    document_1_content = "This is a test sentence and it should be in the vector store"
    document_2_content = "This is another test sentence and it should be removed from the vector store"
    document_2_new_content = "This is one more test sentence and it should be added to the vector store"

    document_1 = DocumentMeta.create_text_document_from_literal(document_1_content)
    document_2 = DocumentMeta.create_text_document_from_literal(document_2_content)

    document_search = DocumentSearch(
        vector_store=text_vector_store,
    )
    await document_search.ingest([document_1, document_2])

    if isinstance(document_2.source, LocalFileSource):
        document_2_path = document_2.source.path
    with open(document_2_path, "w") as file:
        file.write(document_2_new_content)

    await document_search.ingest([document_2])

    document_contents = {entry.text for entry in await text_vector_store.list()}

    assert document_1_content in document_contents
    assert document_2_new_content in document_contents
    assert document_2_content not in document_contents
