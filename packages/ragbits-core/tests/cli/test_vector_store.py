import asyncio
import json

import pytest
from typer.testing import CliRunner

from ragbits.cli import app as root_app
from ragbits.cli import autoregister
from ragbits.core.embeddings.base import Embeddings
from ragbits.core.embeddings.noop import NoopEmbeddings
from ragbits.core.vector_stores import InMemoryVectorStore, VectorStore
from ragbits.core.vector_stores._cli import vector_stores_app
from ragbits.core.vector_stores.base import VectorStoreEntry

example_entries = [
    VectorStoreEntry(id="1", key="entry 1", vector=[4.0, 5.0], metadata={"key": "value"}),
    VectorStoreEntry(id="2", key="entry 2", vector=[1.0, 2.0], metadata={"another_key": "another_value"}),
    VectorStoreEntry(id="3", key="entry 3", vector=[7.0, 8.0], metadata={"foo": "bar", "baz": "qux"}),
]


def vector_store_factory() -> VectorStore:
    """
    A factory function that creates an instance of the VectorStore with example entries.

    Returns:
        VectorStore: An instance of the VectorStore.
    """

    async def add_examples(store: VectorStore) -> None:
        await store.store(example_entries)

    store = InMemoryVectorStore()
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
        _vector_store_for_remove = InMemoryVectorStore()
        asyncio.new_event_loop().run_until_complete(add_examples(_vector_store_for_remove))
    return _vector_store_for_remove


def embedder_factory() -> Embeddings:
    """
    A factory function that creates an instance of no-op Embeddings.

    Returns:
        Embeddings: An instance of the Embeddings.
    """
    return NoopEmbeddings()


def test_vector_store_cli_no_store():
    """
    Test the vector-store CLI command with no store.

    Args:
        cli_runner: A CLI runner fixture.
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(vector_stores_app, ["list"])
    assert "You need to provide the vector store instance be used" in result.stderr


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
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--columns", "id,key,metadata"],
    )
    assert result.exit_code == 0
    assert "entry 1" in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" in result.stdout
    assert "Vector" not in result.stdout
    assert "Id" in result.stdout
    assert "Key" in result.stdout
    assert "Metadata" in result.stdout
    assert "another_key" in result.stdout

    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--columns", "id,key"],
    )
    assert result.exit_code == 0
    assert "entry 1" in result.stdout
    assert "entry 2" in result.stdout
    assert "entry 3" in result.stdout
    assert "Vector" not in result.stdout
    assert "Id" in result.stdout
    assert "Key" in result.stdout
    assert "Metadata" not in result.stdout
    assert "another_key" not in result.stdout


def test_vector_store_list_columns_non_existent():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory", "list", "--columns", "id,key,non_existent"],
    )
    assert result.exit_code == 1
    assert "Unknown column: non_existent" in result.stderr


def test_vector_store_remove():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        vector_stores_app,
        ["--factory-path", "cli.test_vector_store:vector_store_factory_for_remove", "remove", "1", "3"],
    )
    assert result.exit_code == 0
    assert "Removed entries with IDs: 1, 3" in result.stdout

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
            "--embedder-factory-path",
            "cli.test_vector_store:embedder_factory",
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
    entries = [VectorStoreEntry.model_validate(entry) for entry in dicts]
    assert entries == example_entries
