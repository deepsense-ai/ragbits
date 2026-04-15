import asyncio
import json
from uuid import UUID

import pytest
from typer.testing import CliRunner

from ragbits.cli import app as root_app
from ragbits.cli import autoregister
from ragbits.cli.state import CliState, cli_state
from ragbits.core.embeddings.dense import NoopEmbedder
from ragbits.core.vector_stores import InMemoryVectorStore, VectorStore
from ragbits.core.vector_stores._cli import vector_stores_app
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreResult

example_entries = [
    VectorStoreEntry(id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"), text="entry 1", metadata={"key": "value"}),
    VectorStoreEntry(
        id=UUID("367cd073-6a6b-47fe-a032-4bb3a754f6fe"), text="entry 2", metadata={"another_key": "another_value"}
    ),
    VectorStoreEntry(
        id=UUID("d9d11902-f26a-409b-967b-46c30f0b65de"), text="entry 3", metadata={"foo": "bar", "baz": "qux"}
    ),
]


def vector_store_factory() -> VectorStore:
    """
    A factory function that creates an instance of the VectorStore with example entries.

    Returns:
        VectorStore: An instance of the VectorStore.
    """

    async def add_examples(store: VectorStore) -> None:
        await store.store(example_entries)

    store = InMemoryVectorStore(
        embedder=NoopEmbedder(return_values=[[[4.0, 5.0], [1.0, 2.0], [7.0, 8.0]], [[1.0, 1.0]]])
    )
    asyncio.new_event_loop().run_until_complete(add_examples(store))
    return store


# A vector store that's persistant between factory runs,
# to test the remove command.
_vector_store_for_remove: VectorStore | None = None


@pytest.fixture(autouse=True)
def reset_vector_store_for_remove():
    """
    Make sure that the global variable for the vector store used in the remove test is reset before each test.
    """
    global _vector_store_for_remove  # noqa: PLW0603
    _vector_store_for_remove = None


def vector_store_factory_for_remove() -> VectorStore:
    """
    A factory function that creates an instance of the VectorStore with example entries,
    and stores it in a global variable to be used in the remove test.

    Returns:
        VectorStore: An instance of the VectorStore.
    """

    async def add_examples(store: VectorStore) -> None:
        await store.store(example_entries)

    global _vector_store_for_remove  # noqa: PLW0603
    if _vector_store_for_remove is None:
        _vector_store_for_remove = InMemoryVectorStore(embedder=NoopEmbedder())
        asyncio.new_event_loop().run_until_complete(add_examples(_vector_store_for_remove))
    return _vector_store_for_remove


def test_vector_store_cli_no_store():
    """
    Test the vector-store CLI command with no store.

    Args:
        cli_runner: A CLI runner fixture.
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(vector_stores_app, ["list"])
    assert "You need to provide the vector store instance to be used" in result.stderr


def test_vector_store_list():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list"],
    )
    assert result.exit_code == 0
    assert "entry 1" in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" in result.stdout


def test_vector_store_list_limit_offset():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--limit", "1", "--offset", "1"],
    )
    assert result.exit_code == 0
    assert "entry 1" not in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" not in result.stdout


def test_vector_store_list_columns():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--columns", "id,text,metadata"],
    )
    assert result.exit_code == 0
    assert "entry 1" in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" in result.stdout
    assert "Vector" not in result.stdout
    assert "Id" in result.stdout
    assert "Text" in result.stdout
    assert "Metadata" in result.stdout
    assert "another_key" in result.stdout

    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--columns", "id,text"],
    )
    assert result.exit_code == 0
    assert "entry 1" in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" in result.stdout
    assert "Vector" not in result.stdout
    assert "Id" in result.stdout
    assert "Text" in result.stdout
    assert "Metadata" not in result.stdout
    assert "another_key" not in result.stdout


def test_vector_store_list_columns_non_existent():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--columns", "id,text,non_existent"],
    )
    assert result.exit_code == 1
    assert "Unknown column: non_existent" in result.stderr


def test_vector_store_remove():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        [
            "--factory-path",
            "cli.test_vector_store:vector_store_factory_for_remove",
            "remove",
            "48183d3f-61c6-4ef3-bf62-e45d9389acee",
            "d9d11902-f26a-409b-967b-46c30f0b65de",
        ],
    )
    assert result.exit_code == 0
    assert (
        "Removed entries with IDs: 48183d3f-61c6-4ef3-bf62-e45d9389acee, d9d11902-f26a-409b-967b-46c30f0b65de"
        in result.stdout
    )

    result = runner.invoke(
        vector_stores_app, ["--factory-path", "cli.test_vector_store:vector_store_factory_for_remove", "list"]
    )
    assert result.exit_code == 0
    assert "entry 1" not in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" not in result.stdout


def test_vector_store_query():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        [
            "--factory-path",
            "cli.test_vector_store:vector_store_factory",
            "query",
            "--k",
            "1",
            "example query",
        ],
    )
    print(result.stderr)
    assert result.exit_code == 0
    assert "entry 1" not in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" not in result.stdout


def test_vector_store_list_json():
    autoregister()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        root_app,
        [
            "--output",
            "json",
            "vector-store",
            "--factory-path",
            "cli.test_vector_store:vector_store_factory",
            "list",
        ],
    )
    print(result.stderr)
    assert result.exit_code == 0
    dicts = json.loads(result.stdout)
    entries = [VectorStoreEntry.model_validate(result) for result in dicts]
    assert entries == example_entries

    # Reset the output type to the default value so it doesn't affect other tests
    cli_state.output_type = CliState.output_type


def test_vector_store_query_json():
    autoregister()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        root_app,
        [
            "--output",
            "json",
            "vector-store",
            "--factory-path",
            "cli.test_vector_store:vector_store_factory",
            "query",
            "example query",
        ],
    )
    assert result.exit_code == 0
    dicts = json.loads(result.stdout)
    results = [VectorStoreResult.model_validate(result) for result in dicts]
    entries = [result.entry for result in results]
    entries_order = [1, 0, 2]  # by vector similarity
    example_entries_ordered = [example_entries[i] for i in entries_order]
    assert entries == example_entries_ordered

    # Reset the output type to the default value so it doesn't affect other tests
    cli_state.output_type = CliState.output_type
