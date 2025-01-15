from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from ragbits.core.vector_stores import WhereQuery
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.pgvector import PgVectorStore

VECTOR_EXAMPLE = [0.1, 0.2, 0.3]
DATA_JSON_EXAMPLE = [
    {
        "id": "test_id_1",
        "key": "test_key_1",
        "vector": "[0.1, 0.2, 0.3]",
        "metadata": '{"key1": "value1"}',
    },
    {
        "id": "test_id_2",
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
    return PgVectorStore(client=mock_pool, table_name=TEST_TABLE_NAME, vector_size=3)


@pytest.mark.asyncio
async def test_invalid_table_name_raises_error(mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    mock_pool, _ = mock_db_pool
    invalid_table_names = ["123table", "table-name!", "", "table name", "@table"]
    for table_name in invalid_table_names:
        with pytest.raises(ValueError, match=f"Invalid table name: {table_name}"):
            PgVectorStore(client=mock_pool, table_name=table_name, vector_size=3)


def test_create_table_command(mock_pgvector_store: PgVectorStore) -> None:
    result = mock_pgvector_store._create_table_command()
    expected_query = f"""CREATE TABLE {TEST_TABLE_NAME} (id TEXT, key TEXT, vector VECTOR(3), metadata JSONB);"""  # noqa S608
    assert result == expected_query


def test_create_retrieve_query(mock_pgvector_store: PgVectorStore) -> None:
    result = mock_pgvector_store._create_retrieve_query(vector=VECTOR_EXAMPLE)
    expected_query = f"""SELECT * FROM {TEST_TABLE_NAME} ORDER BY vector <=> '[0.1, 0.2, 0.3]' LIMIT 5;"""  # noqa S608
    assert result == expected_query


def test_create_retrieve_query_with_options(mock_pgvector_store: PgVectorStore) -> None:
    mock_pgvector_store._distance_method = "ip"
    result = mock_pgvector_store._create_retrieve_query(
        vector=VECTOR_EXAMPLE, query_options=VectorStoreOptions(max_distance=0.1, k=10)
    )
    expected_query = f"""SELECT * FROM {TEST_TABLE_NAME} WHERE vector <#> '[0.1, 0.2, 0.3]'
            BETWEEN -0.1 AND 0.1 ORDER BY vector <#> '[0.1, 0.2, 0.3]' LIMIT 10;"""  # noqa S608
    assert result == expected_query


def test_create_list_query(mock_pgvector_store: PgVectorStore) -> None:
    where = cast(WhereQuery, {"id": "test_id"})
    result = mock_pgvector_store._create_list_query(where, limit=5, offset=2)
    expected_query = f"""SELECT * FROM {TEST_TABLE_NAME} WHERE id = test_id LIMIT 5 OFFSET 2;"""  # noqa S608
    assert result == expected_query


@pytest.mark.asyncio
async def test_create_table_when_table_exist(
    mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]
) -> None:
    _, mock_conn = mock_db_pool
    with patch.object(
        mock_pgvector_store, "_create_table_command", wraps=mock_pgvector_store._create_table_command
    ) as mock_create_table_command:
        mock_conn.fetchval = AsyncMock(return_value=True)
        await mock_pgvector_store.create_table()
        mock_conn.fetchval.assert_called_once()
        mock_create_table_command.assert_not_called()

        calls = mock_conn.execute.mock_calls
        assert any("CREATE EXTENSION" in str(call) for call in calls)
        assert not any("CREATE TABLE" in str(call) for call in calls)
        assert not any("CREATE INDEX" in str(call) for call in calls)


# TODO: correct test below
# @pytest.mark.asyncio
# async def test_create_table(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
#     _, mock_conn = mock_db_pool
#     with patch.object(
#         mock_pgvector_store, "_create_table_command", wraps=mock_pgvector_store._create_table_command
#     ) as mock_create_table_command:
#         mock_conn.fetchval = AsyncMock(return_value=False)
#         await mock_pgvector_store.create_table()
#         mock_create_table_command.assert_called()
#         mock_conn.fetchval.assert_called_once()
#         calls = mock_conn.execute.mock_calls
#         assert any("CREATE EXTENSION" in str(call) for call in calls)
#         assert any("CREATE TABLE" in str(call) for call in calls)
#         assert any("CREATE INDEX" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_store(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    data = [VectorStoreEntry(id="test_id_1", key="test_key_1", vector=VECTOR_EXAMPLE, metadata={})]
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
    mock_conn.execute.side_effect = asyncpg.exceptions.UndefinedTableError
    data = [VectorStoreEntry(id="test_id_1", key="test_key_1", vector=VECTOR_EXAMPLE, metadata={})]

    with patch.object(mock_pgvector_store, "create_table", new=AsyncMock()) as mock_create_table:
        await mock_pgvector_store.store(data)
        mock_create_table.assert_called_once()
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_remove(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    _, mock_conn = mock_db_pool
    ids_to_remove = ["test_id_1"]
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

    with patch.object(mock_pgvector_store, "create_table", new=AsyncMock()) as mock_create_table:
        await mock_pgvector_store.remove(ids=["test_id"])
        mock_create_table.assert_called_once()
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_records(mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]) -> None:
    query = f"SELECT * FROM {TEST_TABLE_NAME};"  # noqa S608
    data = DATA_JSON_EXAMPLE
    _, mock_conn = mock_db_pool
    mock_conn.fetch = AsyncMock(return_value=data)

    results = await mock_pgvector_store._fetch_records(query=query)
    mock_conn.fetch.assert_called_once()
    calls = mock_conn.fetch.mock_calls
    assert any("SELECT * FROM" in str(call) for call in calls)
    assert len(results) == 2
    assert results[0].id == "test_id_1"
    assert results[0].key == "test_key_1"
    assert results[0].vector == [0.1, 0.2, 0.3]
    assert results[0].metadata == {"key1": "value1"}
    assert results[1].id == "test_id_2"
    assert results[1].key == "test_key_2"
    assert results[1].vector == [0.4, 0.5, 0.6]
    assert results[1].metadata == {"key2": "value2"}


@pytest.mark.asyncio
async def test_fetch_records_no_table(
    mock_pgvector_store: PgVectorStore, mock_db_pool: tuple[MagicMock, AsyncMock]
) -> None:
    _, mock_conn = mock_db_pool
    mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError
    query = "SELECT * FROM some_table;"  # noqa S608

    with patch.object(mock_pgvector_store, "create_table", new=AsyncMock()) as mock_create_table:
        results = await mock_pgvector_store._fetch_records(query=query)
        assert results == []
        mock_create_table.assert_called_once()
    mock_conn.fetch.assert_called_once_with(query)


@pytest.mark.asyncio
async def test_retrieve(mock_pgvector_store: PgVectorStore) -> None:
    vector = VECTOR_EXAMPLE
    options = VectorStoreOptions()
    with (
        patch.object(mock_pgvector_store, "_create_retrieve_query") as mock_create_retrieve_query,
        patch.object(mock_pgvector_store, "_fetch_records") as mock_fetch_records,
    ):
        await mock_pgvector_store.retrieve(vector, options=options)

        mock_create_retrieve_query.assert_called_once()
        mock_fetch_records.assert_called_once()


@pytest.mark.asyncio
async def test_list(mock_pgvector_store: PgVectorStore) -> None:
    with (
        patch.object(mock_pgvector_store, "_create_list_query") as mock_create_list_query,
        patch.object(mock_pgvector_store, "_fetch_records") as mock_fetch_records,
    ):
        await mock_pgvector_store.list(where=None, limit=1, offset=0)
        mock_create_list_query.assert_called_once()
        mock_fetch_records.assert_called_once()
