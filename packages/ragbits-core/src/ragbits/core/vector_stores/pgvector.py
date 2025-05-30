import json
import re
from typing import Any, NamedTuple
from uuid import UUID

import asyncpg
from pydantic.json import pydantic_encoder

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings.base import Embedder, SparseVector, VectorSize
from ragbits.core.embeddings.sparse.base import SparseEmbedder
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreOptionsT,
    VectorStoreResult,
    VectorStoreWithEmbedder,
    WhereQuery,
)


class DistanceOp(NamedTuple):
    """
    Structure for keeping details of distance pgvector's operations.
    """

    function_name: str
    operator: str
    score_formula: str  # formula to calculate score based on distance


DISTANCE_OPS = {
    "cosine": DistanceOp("vector_cosine_ops", "<=>", "1 - distance"),
    "l2": DistanceOp("vector_l2_ops", "<->", "distance * -1"),
    "l1": DistanceOp("vector_l1_ops", "<+>", "distance * -1"),
    "ip": DistanceOp("vector_ip_ops", "<#>", "distance * -1"),
    "bit_hamming": DistanceOp("bit_hamming_ops", "<~>", "distance * -1"),
    "bit_jaccard": DistanceOp("bit_jaccard_ops", "<%>", "distance * -1"),
    "sparsevec_l2": DistanceOp("sparsevec_l2_ops", "<->", "distance * -1"),
    "halfvec_l2": DistanceOp("halfvec_l2_ops", "<->", "distance * -1"),
}


class PgVectorStore(VectorStoreWithEmbedder[VectorStoreOptions]):
    """
    Vector store implementation using [pgvector]
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: asyncpg.Pool,
        table_name: str,
        embedder: Embedder,
        vector_size: int | None = None,
        embedding_type: EmbeddingType = EmbeddingType.TEXT,
        distance_method: str | None = None,
        hnsw_params: dict | None = None,
        default_options: VectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new PgVectorStore instance.

        Args:
            client: The pgVector database connection pool.
            table_name: The name of the table.
            embedder: The embedder to use for converting entries to vectors.
            vector_size: The size of the vectors. If None, will be determined automatically from the embedder.
            embedding_type: Which part of the entry to embed, either text or image. The other part will be ignored.
            distance_method: The distance method to use, default is "cosine" for dense vectors
                and "sparsevec_l2" for sparse vectors.
            hnsw_params: The parameters for the HNSW index. If None, the default parameters will be used.
            default_options: The default options for querying the vector store.
        """
        (
            super().__init__(
                default_options=default_options,
                embedder=embedder,
                embedding_type=embedding_type,
            ),
        )

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        if vector_size is not None and (not isinstance(vector_size, int) or vector_size <= 0):
            raise ValueError("Vector size must be a positive integer.")

        if hnsw_params is None:
            hnsw_params = {"m": 4, "ef_construction": 10}
        elif not isinstance(hnsw_params, dict):
            raise ValueError("hnsw_params must be a dictionary.")
        elif "m" not in hnsw_params or "ef_construction" not in hnsw_params:
            raise ValueError("hnsw_params must contain 'm' and 'ef_construction' keys.")
        elif not isinstance(hnsw_params["m"], int) or hnsw_params["m"] <= 0:
            raise ValueError("m must be a positive integer.")
        elif not isinstance(hnsw_params["ef_construction"], int) or hnsw_params["ef_construction"] <= 0:
            raise ValueError("ef_construction must be a positive integer.")

        if distance_method is None:
            distance_method = "sparsevec_l2" if isinstance(embedder, SparseEmbedder) else "cosine"
        self._client = client
        self._table_name = table_name
        self._vector_size = vector_size
        self._vector_size_info: VectorSize | None = None
        self._distance_method = distance_method
        self._hnsw_params = hnsw_params

    def __reduce__(self) -> tuple:
        """
        Enables the PgVectorStore to be pickled and unpickled.
        """
        # TODO: To be implemented. Required for Ray processing.
        raise NotImplementedError

    async def _get_vector_size_info(self) -> VectorSize:
        """
        Get vector size information from the embedder if not already cached.

        Returns:
            VectorSize information including size and sparsity.
        """
        if self._vector_size_info is None:
            self._vector_size_info = await self._embedder.get_vector_size()
            # Update _vector_size for backward compatibility if it wasn't provided
            if self._vector_size is None:
                self._vector_size = self._vector_size_info.size
        return self._vector_size_info

    async def _get_vector_size(self) -> int:
        """
        Get the vector size, either from the constructor parameter or from the embedder.

        Returns:
            The vector size as an integer.
        """
        if self._vector_size is not None:
            return self._vector_size
        vector_size_info = await self._get_vector_size_info()
        return vector_size_info.size

    def _vector_to_string(self, vector: list[float] | SparseVector) -> str:
        """
        Converts a vector to a string representation.

        Args:
            vector: The vector to convert.

        Returns:
            str: The string representation of the vector.
        """
        if isinstance(vector, SparseVector):
            # For sparse vectors, we need the vector size to be available
            # This will be resolved when this method is called from async context
            vector_size = self._vector_size
            if vector_size is None:
                raise RuntimeError("Vector size must be determined before converting sparse vectors to string")
            points_str = ",".join(f"{i}:{v}" for i, v in zip(vector.indices, vector.values, strict=False))
            return f"{{{points_str}}}/{vector_size}"
        return json.dumps(vector)

    @staticmethod
    def _string_to_vector(vector_str: str) -> list[float] | SparseVector:
        """
        Converts a string representation of a vector to a list of floats.

        Args:
            vector_str: The string representation of the vector.

        Returns:
            list[float] | SparseVector: The vector as a list of floats.
        """
        if vector_str.startswith("{"):
            # Sparse vector
            points = re.findall(r"(\d+):([\d.]+)", vector_str)
            indices, values = zip(*[(int(i), float(v)) for i, v in points], strict=False)
            return SparseVector(indices=list(indices), values=list(values))
        else:
            # Dense vector
            return json.loads(vector_str)

    def _create_retrieve_query(
        self, vector: list[float] | SparseVector, query_options: VectorStoreOptions | None = None
    ) -> tuple[str, list[Any]]:
        """
        Create sql query for retrieving entries from the pgVector collection.

        Args:
            vector: The vector to query.
            query_options: The options for querying the vector store.

        Returns:
            str: sql query.
        """
        distance_operator = DISTANCE_OPS[self._distance_method].operator
        if not query_options:
            query_options = self.default_options

        # We select both distance and score because pgvector require ordering by distance (ascending).
        # in order to use its KNN index. We calculate the score based on the distance.
        score_formula = DISTANCE_OPS[self._distance_method].score_formula.replace(
            "distance", f"(vector {distance_operator} $1)"
        )
        # _table_name has been validated in the class constructor, and it is a valid table name.
        query = f"SELECT *, vector {distance_operator} $1 as distance, {score_formula} as score FROM {self._table_name}"  # noqa S608

        values: list[Any] = [self._vector_to_string(vector)]
        where_clauses = []

        if query_options.score_threshold is not None:
            where_clauses.append("score >= $" + str(len(values) + 1))
            values.append(query_options.score_threshold)

        if query_options.where:
            where_clauses.append(f"metadata @> ${len(values) + 1}")
            values.append(json.dumps(query_options.where))

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY distance"

        if query_options.k:
            query += f" LIMIT ${len(values) + 1}"
            values.append(query_options.k)
        query += ";"

        return query, values

    def _create_list_query(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> tuple[str, list[Any]]:
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

        query = f"SELECT * FROM {self._table_name} WHERE metadata @> $1 LIMIT $2 OFFSET $3;"  # noqa S608
        values = [
            json.dumps(where) if where else "{}",
            limit,
            offset or 0,
        ]
        return query, values

    async def _check_table_exists(self) -> bool:
        check_table_existence = """
                SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = $1
            ); """
        async with self._client.acquire() as conn:
            return await conn.fetchval(check_table_existence, self._table_name)

    async def create_table(self) -> None:
        """
        Create a pgVector table with an HNSW index for given similarity.
        """
        vector_size = await self._get_vector_size()
        with trace(
            table_name=self._table_name,
            distance_method=self._distance_method,
            vector_size=vector_size,
            hnsw_index_parameters=self._hnsw_params,
        ):
            distance = DISTANCE_OPS[self._distance_method].function_name
            create_vector_extension = "CREATE EXTENSION IF NOT EXISTS vector;"
            # _table_name and has been validated in the class constructor, and it is a valid table name.
            # vector_size has been validated in the class constructor or obtained from embedder,
            # and it is a valid vector size.

            is_sparse = isinstance(self._embedder, SparseEmbedder)
            vector_func = "VECTOR" if not is_sparse else "SPARSEVEC"

            create_table_query = f"""
            CREATE TABLE {self._table_name}
            (id UUID, text TEXT, image_bytes BYTEA, vector {vector_func}({vector_size}), metadata JSONB);
            """
            # _hnsw_params has been validated in the class constructor, and it is valid dict[str,int].
            create_index_query = f"""
                    CREATE INDEX {self._table_name + "_hnsw_idx"} ON {self._table_name}
                    USING hnsw (vector {distance})
                    WITH (m = {self._hnsw_params["m"]}, ef_construction = {self._hnsw_params["ef_construction"]});
                    """
            if await self._check_table_exists():
                print(f"Table {self._table_name} already exist!")
                return
            async with self._client.acquire() as conn:
                await conn.execute(create_vector_extension)

                try:
                    async with conn.transaction():
                        await conn.execute(create_table_query)
                        await conn.execute(create_index_query)

                    print("Table and index created!")
                except Exception as e:
                    print(f"Failed to create table and index: {e}")
                    raise

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the pgVector collection.

        Args:
            entries: The entries to store.
        """
        if not entries:
            return

        # Ensure vector size is determined before processing
        vector_size = await self._get_vector_size()

        # _table_name has been validated in the class constructor, and it is a valid table name.
        insert_query = f"""
        INSERT INTO {self._table_name} (id, text, image_bytes, vector, metadata)
        VALUES ($1, $2, $3, $4, $5)
        """  # noqa S608
        with trace(
            table_name=self._table_name,
            entries=entries,
            vector_size=vector_size,
            embedder=repr(self._embedder),
            embedding_type=self._embedding_type,
        ):
            embeddings = await self._create_embeddings(entries)
            exists = await self._check_table_exists()
            if not exists:
                print(f"Table {self._table_name} does not exist. Creating the table.")
                try:
                    await self.create_table()
                except Exception as e:
                    print(f"Failed to handle missing table: {e}")
                    return

            async with self._client.acquire() as conn:
                for entry in entries:
                    if entry.id not in embeddings:
                        continue

                    await conn.execute(
                        insert_query,
                        str(entry.id),
                        entry.text,
                        entry.image_bytes,
                        self._vector_to_string(embeddings[entry.id]),
                        json.dumps(entry.metadata, default=pydantic_encoder),
                    )

    async def remove(self, ids: list[UUID]) -> None:
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
        with trace(table_name=self._table_name, ids=ids):
            try:
                async with self._client.acquire() as conn:
                    await conn.execute(remove_query, ids)
            except asyncpg.exceptions.UndefinedTableError:
                print(f"Table {self._table_name} does not exist.")
                return

    async def retrieve(
        self,
        text: str,
        options: VectorStoreOptionsT | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieves entries from the pgVector collection.

        Args:
            text: The text to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        # Ensure vector size is determined before processing
        vector_size = await self._get_vector_size()

        with trace(
            text=text,
            options=merged_options.dict(),
            table_name=self._table_name,
            vector_size=vector_size,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
            embedding_type=self._embedding_type,
        ) as outputs:
            query_vector = (await self._embedder.embed_text([text]))[0]
            query, values = self._create_retrieve_query(query_vector, merged_options)

            try:
                async with self._client.acquire() as conn:
                    results = await conn.fetch(query, *values)

                outputs.results = [
                    VectorStoreResult(
                        entry=VectorStoreEntry(
                            id=record["id"],
                            text=record["text"],
                            image_bytes=record["image_bytes"],
                            metadata=json.loads(record["metadata"]),
                        ),
                        vector=self._string_to_vector(record["vector"]),
                        score=record["score"],
                    )
                    for record in results
                ]

            except asyncpg.exceptions.UndefinedTableError:
                print(f"Table {self._table_name} does not exist.")
                outputs.results = []
            return outputs.results

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
        with trace(table=self._table_name, query=where, limit=limit, offset=offset) as outputs:
            list_query, values = self._create_list_query(where, limit, offset)
            try:
                async with self._client.acquire() as conn:
                    results = await conn.fetch(list_query, *values)
                outputs.listed_entries = [
                    VectorStoreEntry(
                        id=record["id"],
                        text=record["text"],
                        image_bytes=record["image_bytes"],
                        metadata=json.loads(record["metadata"]),
                    )
                    for record in results
                ]

            except asyncpg.exceptions.UndefinedTableError:
                print(f"Table {self._table_name} does not exist.")
                outputs.listed_entries = []
            return outputs.listed_entries
