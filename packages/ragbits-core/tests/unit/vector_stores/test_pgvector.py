from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import asyncpg
import pytest

from ragbits.core.embeddings.noop import NoopEmbedder
from ragbits.core.vector_stores import WhereQuery
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.pgvector import PgVectorStore

VECTOR_EXAMPLE = [0.1, 0.2, 0.3]
DATA_JSON_EXAMPLE = [
    {
        "id": "8c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
        "key": "test_key_1",
        "vector": "[0.1, 0.2, 0.3]",
        "metadata": '{"key1": "value1"}',
    },
    {
        "id": "9c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
        "key": "test_key_2",
        "vector": "[0.4, 0.5, 0.6]",
        "metadata": '{"key2": "value2"}',
    },
]
TEST_TABLE_NAME = "test_table"


@pytest.fixture
def mock_db_pool() -> tuple[MagicMock, AsyncMock]:
    """Fixture to mock the asyncpg connection pool."""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    return mock_pool, mock_conn


@pytest.fixture
def mock_pgvector_store(mock_db_pool: tuple[MagicMock, AsyncMock]) -> PgVectorStore:
    """Fixture to create a PgVectorStore instance with mocked connection pool."""
    mock_pool, _ = mock_db_pool
    return PgVectorStore(client=mock_pool, table_name=TEST_TABLE_NAME, vector_size=3, embedder=NoopEmbedder())


@pytest.mark.asyncio
async def test_invalid_table_name_raises_error(mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    mock_pool, _ = mock_db_pool
    invalid_table_names = ["123table", "table-name!", "", "table name", "@table"]
    for table_name in invalid_table_names:
        with pytest.raises(ValueError, match=f"Invalid table name: {table_name}"):
            PgVectorStore(client=mock_pool, table_name=table_name, vector_size=3, embedder=NoopEmbedder())


@pytest.mark.asyncio
async def test_invalid_vector_size_raises_error(mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    mock_pool, _ = mock_db_pool
    vector_size_values = ["546", -23.0, 0, 46.5, [2, 3, 4], {"vector_size": 6}]
    for vector_size in vector_size_values:
        with pytest.raises(ValueError, match="Vector size must be a positive integer."):
            PgVectorStore(
                client=mock_pool,
                table_name=TEST_TABLE_NAME,
                vector_size=vector_size,  # type: ignore
                embedder=NoopEmbedder(),
            )


@pytest.mark.asyncio
async def test_invalid_hnsw_raises_error(mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    mock_pool, _ = mock_db_pool
    hnsw_values = ["546", 0, [5, 10], {"m": 2}, {"m": "-23", "ef_construction": 12}, {"m": 23, "ef_construction": -12}]
    for hnsw in hnsw_values:
        with pytest.raises(ValueError):
            PgVectorStore(
                client=mock_pool,
                table_name=TEST_TABLE_NAME,
                vector_size=3,
                hnsw_params=hnsw,  # type: ignore
                embedder=NoopEmbedder(),
            )


def test_create_retrieve_query(mock_pgvector_store: PgVectorStore) -> None:
    result, values = mock_pgvector_store._create_retrieve_query(vector=VECTOR_EXAMPLE)
    expected_query = f"""SELECT *, vector <=> $1 as distance FROM {TEST_TABLE_NAME} ORDER BY distance LIMIT $2;"""  # noqa S608
    expected_values = ["[0.1, 0.2, 0.3]", 5]
    assert result == expected_query
    assert values == expected_values


def test_create_retrieve_query_with_options(mock_pgvector_store: PgVectorStore) -> None:
    result, values = mock_pgvector_store._create_retrieve_query(
        vector=VECTOR_EXAMPLE, query_options=VectorStoreOptions(max_distance=0.1, k=10)
    )
    expected_query = f"""SELECT *, vector <=> $1 as distance FROM {TEST_TABLE_NAME} WHERE distance < $2 ORDER BY distance LIMIT $3;"""  # noqa S608
    expected_values = ["[0.1, 0.2, 0.3]", 0.1, 10]
    assert result == expected_query
    assert values == expected_values


def test_create_retrieve_query_with_options_for_ip_distance(mock_pgvector_store: PgVectorStore) -> None:
    mock_pgvector_store._distance_method = "ip"
    result, values = mock_pgvector_store._create_retrieve_query(
        vector=VECTOR_EXAMPLE, query_options=VectorStoreOptions(max_distance=0.1, k=10)
    )
    expected_query = f"""SELECT *, vector <#> $1 as distance FROM {TEST_TABLE_NAME} WHERE distance BETWEEN $2 AND $3 ORDER BY distance LIMIT $4;"""  # noqa S608
    expected_values = ["[0.1, 0.2, 0.3]", -0.1, 0.1, 10]
    assert result == expected_query
    assert values == expected_values


def test_create_list_query(mock_pgvector_store: PgVectorStore) -> None:
    where = cast(WhereQuery, {"id": "test_id", "document.title": "test title"})
    result, values = mock_pgvector_store._create_list_query(where, limit=5, offset=2)
    expected_query = f"""SELECT * FROM {TEST_TABLE_NAME} WHERE metadata @> $1 LIMIT $2 OFFSET $3;"""  # noqa S608
    expected_values = ['{"id": "test_id", "document.title": "test title"}', 5, 2]
    assert result == expected_query
    assert values == expected_values


def test_create_list_query_without_options(mock_pgvector_store: PgVectorStore) -> None:
    result, values = mock_pgvector_store._create_list_query()
    expected_query = f"""SELECT * FROM {TEST_TABLE_NAME} WHERE metadata @> $1 LIMIT $2 OFFSET $3;"""  # noqa S608
    expected_values = ["{}", None, 0]
    assert result == expected_query
    assert values == expected_values


@pytest.mark.asyncio
async def test_create_table_when_table_exist(
    mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]
) -> None:
    _, mock_conn = mock_db_pool
    mock_conn.fetchval = AsyncMock(return_value=True)
    await mock_pgvector_store.create_table()
    mock_conn.fetchval.assert_called_once()
    calls = mock_conn.execute.mock_calls
    assert any("CREATE EXTENSION" in str(call) for call in calls)
    assert not any("CREATE TABLE" in str(call) for call in calls)
    assert not any("CREATE INDEX" in str(call) for call in calls)


# TODO: correct test below
# @pytest.mark.asyncio
# async def test_create_table(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
#     _, mock_conn = mock_db_pool
#     mock_conn.fetchval = AsyncMock(return_value=False)
#     await mock_pgvector_store.create_table()
#     mock_conn.fetchval.assert_called_once()
#     calls = mock_conn.execute.mock_calls
#     assert any("CREATE EXTENSION" in str(call) for call in calls)
#     assert any("CREATE TABLE" in str(call) for call in calls)
#     assert any("CREATE INDEX" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_store(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    data = [VectorStoreEntry(id=UUID("64144806-e080-4f9c-b46d-682fe4871497"), text="test_key_1", metadata={})]
    await mock_pgvector_store.store(data)
    mock_conn.execute.assert_called()
    calls = mock_conn.execute.mock_calls
    assert any("INSERT INTO" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_store_no_entries(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool

    with patch.object(mock_pgvector_store, "create_table", wraps=mock_pgvector_store.create_table) as mock_create_table:
        await mock_pgvector_store.store(entries=None)  # type: ignore[arg-type]
        mock_create_table.assert_not_called()
        mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_store_no_table(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    mock_conn.execute.side_effect = [asyncpg.exceptions.UndefinedTableError, None]
    data = [VectorStoreEntry(id=UUID("eeb67aa6-0411-4dc3-9647-c7b3182e0594"), text="test_key_1", metadata={})]

    with patch.object(mock_pgvector_store, "create_table", new=AsyncMock()) as mock_create_table:
        await mock_pgvector_store.store(data)
        mock_create_table.assert_called_once()
    assert mock_conn.execute.call_count == 2


@pytest.mark.asyncio
async def test_remove(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    ids_to_remove = [UUID("6edae3b9-087b-4e09-a452-ab2235e023c8")]
    await mock_pgvector_store.remove(ids_to_remove)
    mock_conn.execute.assert_called_once()
    calls = mock_conn.execute.mock_calls
    assert any("DELETE FROM" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_remove_no_ids(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    await mock_pgvector_store.remove(ids=None)  # type: ignore[arg-type]
    mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_remove_no_table(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    mock_conn.execute.side_effect = asyncpg.exceptions.UndefinedTableError
    with patch("builtins.print") as mock_print:
        await mock_pgvector_store.remove(ids=[UUID("6edae3b9-087b-4e09-a452-ab2235e023c8")])
        mock_conn.execute.assert_called_once()
        mock_print.assert_called_once_with(f"Table {TEST_TABLE_NAME} does not exist.")


@pytest.mark.asyncio
async def test_fetch_records(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    query = f"SELECT * FROM {TEST_TABLE_NAME};"  # noqa S608
    data = DATA_JSON_EXAMPLE
    _, mock_conn = mock_db_pool
    mock_conn.fetch = AsyncMock(return_value=data)

    results = await mock_pgvector_store._fetch_records(query=query, values=[])
    mock_conn.fetch.assert_called_once()
    calls = mock_conn.fetch.mock_calls
    assert any("SELECT * FROM" in str(call) for call in calls)
    assert len(results) == 2
    assert results[0].id == UUID("8c7d6b27-4ef1-537c-ad7c-676edb8bc8a8")
    assert results[0].text == "test_key_1"
    assert results[0].metadata == {"key1": "value1"}
    assert results[1].id == UUID("9c7d6b27-4ef1-537c-ad7c-676edb8bc8a8")
    assert results[1].text == "test_key_2"
    assert results[1].metadata == {"key2": "value2"}


@pytest.mark.asyncio
async def test_fetch_records_no_table(
    mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]
) -> None:
    _, mock_conn = mock_db_pool
    mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError
    query = "SELECT * FROM some_table;"  # noqa S608
    with patch("builtins.print") as mock_print:
        results = await mock_pgvector_store._fetch_records(query=query, values=[])
        assert results == []
        mock_conn.fetch.assert_called_once()
        mock_print.assert_called_once_with(f"Table {TEST_TABLE_NAME} does not exist.")


@pytest.mark.asyncio
async def test_list(mock_pgvector_store: PgVectorStore) -> None:
    with (
        patch.object(mock_pgvector_store, "_create_list_query") as mock_create_list_query,
        patch.object(mock_pgvector_store, "_fetch_records") as mock_fetch_records,
    ):
        mock_create_list_query.return_value = ("query_string", [1, 0])
        await mock_pgvector_store.list(where=None, limit=1, offset=0)
        mock_create_list_query.assert_called_once()
        mock_fetch_records.assert_called_once()
