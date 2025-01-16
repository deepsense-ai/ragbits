import json
import re
from typing import get_type_hints

import asyncpg
from pydantic.json import pydantic_encoder

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery

DISTANCE_OPS = {
    "cosine": ("vector_cosine_ops", "<=>"),
    "l2": ("vector_l2_ops", "<->"),
    "l1": ("vector_l1_ops", "<+>"),
    "ip": ("vector_ip_ops", "<#>"),
    "bit_hamming": ("bit_hamming_ops", "<~>"),
    "bit_jaccard": ("bit_jaccard_ops", "<%>"),
    "sparsevec_l2": ("sparsevec_l2_ops", "<->"),
    "halfvec_l2": ("halfvec_l2_ops", "<->"),
}


class PgVectorStore(VectorStore[VectorStoreOptions]):
    """
    Vector store implementation using [pgvector]
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: asyncpg.Pool,
        table_name: str,
        vector_size: int = 512,
        distance_method: str = "cosine",
        hnsw_params: dict | None = None,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new PgVectorStore instance.

        Args:
            client: The pgVector database connection pool.
            table_name: The name of the table.
            vector_size: The size of the vectors.
            distance_method: The distance method to use.
            hnsw_params: The parameters for the HNSW index. If None, the default parameters will be used.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in pgVector db.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            raise ValueError(f"Invalid table name: {table_name}")

        if hnsw_params is None:
            hnsw_params = {"m": 4, "ef_construction": 10}
        self._client = client
        self._table_name = table_name
        self._vector_size = vector_size
        self._distance_method = distance_method
        self._hnsw_params = hnsw_params

    def _create_table_command(self) -> str:
        """
        Create sql query for creating a pgVector table.

        Returns:
              str: sql query.
        """
        type_mapping = {
            str: "TEXT",
            list: f"VECTOR({self._vector_size})",
            dict: "JSONB",
        }
        columns = []
        type_hints = get_type_hints(VectorStoreEntry)
        for column, column_type in type_hints.items():
            if column_type == list[float]:
                columns.append(f"{column} {type_mapping[list]}")
            else:
                sql_type = type_mapping.get(column_type)
                columns.append(f"{column} {sql_type}")

        return f"CREATE TABLE {self._table_name} (" + ", ".join(columns) + ");"

    def _create_retrieve_query(self, vector: list[float], query_options: VectorStoreOptions | None = None) -> str:
        """
        Create sql query for retrieving entries from the pgVector collection.

        Args:
            vector: The vector to query.
            query_options: The options for querying the vector store.

        Returns:
            str: sql query.
        """
        distance_operator = DISTANCE_OPS[self._distance_method][1]
        # _table_name has been validated in the class constructor, and it is a valid table name.
        query = f"SELECT * FROM {self._table_name}"  # noqa S608
        if not query_options:
            query_options = self.default_options
        if query_options.max_distance and self._distance_method == "ip":
            query += f""" WHERE vector {distance_operator} '{vector}'
            BETWEEN {(-1) * query_options.max_distance} AND {query_options.max_distance}"""
        elif query_options.max_distance:
            query += f" WHERE vector {distance_operator} '{vector}' < {query_options.max_distance}"
        query += f" ORDER BY vector {distance_operator} '{vector}'"
        if query_options.k:
            query += f" LIMIT {query_options.k}"

        query += ";"

        return query

    def _create_list_query(self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0) -> str:
        """
        Create sql query for listing entries from the pgVector collection.

        Args:
            where: The filter dictionary - the keys are the field names and the values are the values to filter by.
                Not specifying the key means no filtering.
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            sql query.
        """
        # _table_name has been validated in the class constructor, and it is a valid table name.
        query = f"SELECT * FROM {self._table_name}"  # noqa S608
        if where:
            filters = []
            for key, value in where.items():
                filters.append(f"{key} = {value}")
            query += " WHERE " + " AND ".join(filters)

        if limit is not None:
            query += f" LIMIT {limit}"

        if offset is not None:
            query += f" OFFSET {offset}"

        query += ";"
        return query

    async def create_table(self) -> None:
        """
        Create a pgVector table with an HNSW index for given similarity.
        """
        check_table_existence = """
                SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = $1
            ); """

        create_vector_extension = "CREATE EXTENSION IF NOT EXISTS vector;"
        # _table_name has been validated in the class constructor, and it is a valid table name.
        create_index_query = f"""
                CREATE INDEX {self._table_name + "_hnsw_idx"} ON {self._table_name}
                USING hnsw (vector {DISTANCE_OPS[self._distance_method][0]})
                WITH (m = {self._hnsw_params["m"]}, ef_construction = {self._hnsw_params["ef_construction"]});
                """

        async with self._client.acquire() as conn:
            await conn.execute(create_vector_extension)
            exists = await conn.fetchval(check_table_existence, self._table_name)

            if not exists:
                create_table_query = self._create_table_command()
                try:
                    async with conn.transaction():
                        await conn.execute(create_table_query)
                        await conn.execute(create_index_query)

                    print("Table and index created!")
                except Exception as e:
                    print(f"Failed to create table and index: {e}")
                    raise
            else:
                print("Table already exists!")

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the pgVector collection.

        Args:
            entries: The entries to store.
        """
        if not entries:
            return
        # _table_name has been validated in the class constructor, and it is a valid table name.
        insert_query = f"""
        INSERT INTO {self._table_name} (id, key, vector, metadata)
        VALUES ($1, $2, $3, $4)
        """  # noqa S608

        try:
            async with self._client.acquire() as conn:
                for entry in entries:
                    await conn.execute(
                        insert_query,
                        entry.id,
                        entry.key,
                        str(entry.vector),
                        json.dumps(entry.metadata, default=pydantic_encoder),
                    )
        except asyncpg.exceptions.UndefinedTableError:
            print(f"Table {self._table_name} does not exist. Creating the table.")
            try:
                await self.create_table()
            except Exception as e:
                print(f"Failed to handle missing table: {e}")
                return

            print("Table created successfully. Inserting entries...")
            await self.store(entries)

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        if not ids:
            print("No IDs provided, nothing to remove")
            return
        # _table_name has been validated in the class constructor, and it is a valid table name.
        remove_query = f"""
        DELETE FROM {self._table_name}
        WHERE id = ANY($1)
        """  # noqa S608

        try:
            async with self._client.acquire() as conn:
                await conn.execute(remove_query, ids)
        except asyncpg.exceptions.UndefinedTableError:
            print(f"Table {self._table_name} does not exist.")
            return

    @traceable
    async def _fetch_records(self, query: str) -> list[VectorStoreEntry]:
        """
        Fetch records from the pgVector collection.

        Args:
            query: sql query
        Returns:
            list of VectorStoreEntry objects.
        """
        try:
            async with self._client.acquire() as conn:
                results = await conn.fetch(query)

            return [
                VectorStoreEntry(
                    id=record["id"],
                    key=record["key"],
                    vector=json.loads(record["vector"]),
                    metadata=json.loads(record["metadata"]),
                )
                for record in results
            ]

        except asyncpg.exceptions.UndefinedTableError:
            print(f"Table {self._table_name} does not exist.")
            return []

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the pgVector collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
        query_options = (self.default_options | options) if options else self.default_options
        retrieve_query = self._create_retrieve_query(vector, query_options)
        return await self._fetch_records(retrieve_query)

    @traceable
    async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector store. The entries can be filtered, limited and offset.

        Args:
            where: The filter dictionary - the keys are the field names and the values are the values to filter by.
                Not specifying the key means no filtering.
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.
        """
        list_query = self._create_list_query(where, limit, offset)
        return await self._fetch_records(list_query)
