import json
from typing import get_type_hints

import asyncpg

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery


class PgVectorDistance:
    """
    Supported distance methods for pgVector.
    """

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
        vector_size: int  = 512,
        distance_method: str  = "cosine",
        hnsw_params=None,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            table_name: The name of the table.
            db: The database connection string.
            vector_size: The size of the vectors.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in pgVector db.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)
        if hnsw_params is None:
            hnsw_params = {"m": 4, "ef_construction": 10}
        self.client = client
        self.table_name = table_name
        self.vector_size = vector_size
        self.distance_method = distance_method
        self.hnsw_params = hnsw_params

    def _create_table_command(self) -> str:
        """
        Create sql query for creating a pgVector table.

        Returns:
              str: sql query.
        """
        type_mapping = {
            str: "TEXT",
            list: f"VECTOR({self.vector_size})",  # Requires vector_size
            dict: "JSONB",
        }
        columns = []
        type_hints = get_type_hints(VectorStoreEntry)
        for column, column_type in type_hints.items():
            if column_type == list[float]:  # Handle VECTOR type
                columns.append(f"{column} {type_mapping[list]}")
            else:
                sql_type = type_mapping.get(column_type)
                columns.append(f"{column} {sql_type}")

        return f"CREATE TABLE {self.table_name} (" + ", ".join(columns) + ");"

    def _create_retrieve_query(self, vector: list[float], query_options: VectorStoreOptions | None = None) -> str:
        """
        Create sql query for retrieving entries from the pgVector collection.

        Args:
            vector: The vector to query.
            query_options: The options for querying the vector store.

        Returns:
            str: sql query.
        """
        distance_operator = PgVectorDistance.DISTANCE_OPS[self.distance_method][1]

        query = f"SELECT * FROM {self.table_name}"  # noqa S608
        if not query_options:
            query_options= self.default_options
        if query_options.max_distance and self.distance_method == "ip":
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
        query = f"SELECT * FROM {self.table_name}"  # noqa S608
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

        create_index_query = """
                CREATE INDEX {} ON {}
                USING hnsw (vector {})
                WITH (m = {}, ef_construction = {});
                """



        async with self.client.acquire() as conn:
            await conn.execute(create_vector_extension)
            exists = await conn.fetchval(check_table_existence, self.table_name)

            if not exists:
                create_command = self._create_table_command()
                await conn.execute(create_command)
                hnsw_name = self.table_name + "_hnsw_idx"
                query = create_index_query.format(
                    hnsw_name,
                    self.table_name,
                    PgVectorDistance.DISTANCE_OPS[self.distance_method][0],
                    self.hnsw_params["m"],
                    self.hnsw_params["ef_construction"],
                )
                await conn.execute(query)
                print("Index created!")

            else:
                print("Index already exists!")



    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the pgVector collection.

        Args:
            entries: The entries to store.
        """
        if not entries:
            return

        insert_query = """
        INSERT INTO {} (id, key, vector, metadata)
        VALUES ($1, $2, $3, $4)
        """


        try:
            async with self.client.acquire() as conn:
                for entry in entries:
                    await conn.execute(
                        insert_query.format(self.table_name),
                        entry.id,
                        entry.key,
                        str(entry.vector),
                        json.dumps(entry.metadata),
                    )
        except asyncpg.exceptions.UndefinedTableError:
            print(f"Table {self.table_name} does not exist. Creating the table.")
            await self.create_table()


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

        remove_query = """
        DELETE FROM {}
        WHERE id = ANY($1)
        """

        try:
            async with self.client.acquire() as conn:
                await conn.execute(remove_query.format(self.table_name), ids)
        except asyncpg.exceptions.UndefinedTableError:
            print(f"Table {self.table_name} does not exist. Creating the table.")
            await self.create_table()



    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the pgVector collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.


        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        query_options = (self.default_options | options) if options else self.default_options
        retrieve_query = self._create_retrieve_query(vector, query_options)


        try:
            async with self.client.acquire() as conn:
                results = await conn.fetch(retrieve_query)

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
            print(f"Table {self.table_name} does not exist. Creating the table.")
            await self.create_table()
            return []



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

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        list_query = self._create_list_query(where, limit, offset)

        try:
            async with self.client.acquire() as conn:
                results = await conn.fetch(list_query)

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
            print(f"Table {self.table_name} does not exist. Creating the table.")
            await self.create_table()
            return []

