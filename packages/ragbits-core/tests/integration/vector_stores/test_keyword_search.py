from functools import partial
from pathlib import Path
from uuid import UUID

import pytest
import weaviate

from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreWithEmbedder,
)
from ragbits.core.vector_stores.weaviate import WeaviateVectorStore, WeaviateVectorStoreOptions

IMAGES_PATH = Path(__file__).parent.parent.parent / "assets" / "img"


@pytest.fixture(
    name="vector_store_cls",
    params=[
        lambda _: partial(
            WeaviateVectorStore, client=weaviate.use_async_with_local(), index_name="test_keyword_index_name"
        ),
    ],
    ids=["WeaviateVectorStore"],
)
async def vector_store_cls_fixture(
    request: pytest.FixtureRequest,
) -> type[VectorStoreWithEmbedder]:
    """
    Returns vector stores classes with different backends, with backend-specific parameters already set,
    but parameters common to VectorStoreWithEmbedder left to be set.
    """
    return request.param(None)


@pytest.fixture(name="vector_store")
def vector_store_fixture(
    vector_store_cls: type[VectorStoreWithEmbedder],
) -> VectorStoreWithEmbedder:
    """
    For Weaviate vector store in `vector_store_cls`, returns an instance with noop embedder
    (as embedder is not used for keyword search) and keyword search enabled.
    """
    options = WeaviateVectorStoreOptions(use_keyword_search=True)
    return vector_store_cls(embedder=NoopEmbedder(), default_options=options)


@pytest.fixture(name="vector_store_keyword_search_entries")
def vector_store_keyword_search_entries_fixture() -> list[VectorStoreEntry]:
    with open(IMAGES_PATH / "test.png", "rb") as file:
        first_image_bytes = file.read()
    with open(IMAGES_PATH / "test2.jpg", "rb") as file:
        second_image_bytes = file.read()
    return [
        VectorStoreEntry(
            id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"),
            text="This text is about parrots and cats.",
            metadata={
                "foo": "bar",
                "nested_foo": {"nested_bar": "nested_baz"},
                "some_int": 1,
                "some_bool": True,
                "some_float": 1.0,
                "simple": "no_simple_value",
            },
        ),
        VectorStoreEntry(
            id=UUID("367cd073-6a6b-47fe-a032-4bb3a754f6fe"),
            image_bytes=first_image_bytes,
        ),
        VectorStoreEntry(
            id=UUID("d9d11902-f26a-409b-967b-46c30f0b65de"),
            image_bytes=second_image_bytes,
            text="It is a document about animals.",
            metadata={
                "some_int": 2,
                "some_bool": False,
                "some_float": 2.0,
                "baz": "qux",
                "simple": "simple_value",
                "nested_foo": {"nested_bar": "no_nested_baz"},
            },
        ),
    ]


async def test_vector_store_list(
    vector_store: VectorStoreWithEmbedder,
    vector_store_keyword_search_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_keyword_search_entries)
    result_entries = await vector_store.list()
    expected_entries = (
        [e for e in vector_store_keyword_search_entries if e.text is not None]
        if vector_store._embedding_type == EmbeddingType.TEXT
        else [e for e in vector_store_keyword_search_entries if e.image_bytes is not None]
    )

    sorted_results = sorted(result_entries, key=lambda entry: entry.id)
    sorted_expected = sorted(expected_entries, key=lambda entry: entry.id)

    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.id == expected.id

        # Chroma is unable to store None values so unfortunately we have to tolerate empty strings
        assert result.text == expected.text or (expected.text is None and result.text == "")
        assert result.metadata == expected.metadata
        assert result.image_bytes == expected.image_bytes


@pytest.mark.parametrize(
    "filter",
    [
        ("simple", {"simple": "simple_value"}),
        ("nested_foo", {"nested_foo": {"nested_bar": "nested_baz"}}),
        ("some_int", {"some_int": 1}),
        ("some_bool", {"some_bool": False}),
        ("some_float", {"some_float": 1.0}),
    ],
)
async def test_vector_store_list_with_filter(
    vector_store: VectorStoreWithEmbedder,
    vector_store_keyword_search_entries: list[VectorStoreEntry],
    filter: tuple[str, dict],
) -> None:
    await vector_store.store(vector_store_keyword_search_entries)
    result_entries = await vector_store.list(filter[1])
    expected_entries = [
        e for e in vector_store_keyword_search_entries if e.metadata.get(filter[0], None) == filter[1][filter[0]]
    ]
    sorted_results = sorted(result_entries, key=lambda entry: entry.id)
    sorted_expected = sorted(expected_entries, key=lambda entry: entry.id)

    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.id == expected.id

        # Chroma is unable to store None values so unfortunately we have to tolerate empty strings
        assert result.text == expected.text or (expected.text is None and result.text == "")
        assert result.metadata == expected.metadata
        assert result.image_bytes == expected.image_bytes


async def test_vector_store_remove(
    vector_store: VectorStoreWithEmbedder,
    vector_store_keyword_search_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_keyword_search_entries)
    await vector_store.remove([vector_store_keyword_search_entries[2].id])

    result_entries = await vector_store.list()
    assert len(result_entries) == 1
    assert vector_store_keyword_search_entries[2].id not in {entry.id for entry in result_entries}


async def test_vector_store_retrieve(
    vector_store: VectorStoreWithEmbedder,
    vector_store_keyword_search_entries: list[VectorStoreEntry],
) -> None:
    query = "cats"
    await vector_store.store(vector_store_keyword_search_entries)
    result_entries = await vector_store.retrieve(
        text=query, options=WeaviateVectorStoreOptions(use_keyword_search=True)
    )
    expected_entries = [e for e in vector_store_keyword_search_entries if e.text is not None and query in e.text]

    sorted_results = sorted(result_entries, key=lambda r: r.entry.id)
    sorted_expected = sorted(expected_entries, key=lambda entry: entry.id)

    prev_score = float("inf")
    for result, expected in zip(sorted_results, sorted_expected, strict=True):
        assert result.entry.id == expected.id

        assert result.score <= prev_score  # Ensure that the results are sorted by score and bigger is better
        prev_score = result.score

        assert result.entry.text == expected.text
        assert result.entry.metadata == expected.metadata
        assert result.entry.image_bytes == expected.image_bytes


async def test_vector_store_retrieve_order(
    vector_store: VectorStoreWithEmbedder,
    vector_store_keyword_search_entries: list[VectorStoreEntry],
) -> None:
    await vector_store.store(vector_store_keyword_search_entries)

    query = "cats"
    results = await vector_store.retrieve(text=query, options=WeaviateVectorStoreOptions(k=1, use_keyword_search=True))
    assert len(results) == 1
    expected_entry = vector_store_keyword_search_entries[0]
    assert results[0].entry.id == expected_entry.id

    query = "animals"
    results = await vector_store.retrieve(text=query, options=WeaviateVectorStoreOptions(k=1, use_keyword_search=True))
    assert len(results) == 1
    expected_entry = vector_store_keyword_search_entries[2]
    assert results[0].entry.id == expected_entry.id
