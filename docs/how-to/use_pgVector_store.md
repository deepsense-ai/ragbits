# How to use pgVector database with Ragbits

sudo docker pull pgvector/pgvector:pg16

```
sudo docker run --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword -d pgvector/pgvector:pg16
```

DB = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"


import asyncpg
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions
from ragbits.core.vector_stores.pgvector import PgVectorStore
    connection = await asyncpg.create_pool(DB)
    vector_store = PgVectorStore(connection, "test_index9831")


    pool = await asyncpg.create_pool(
        user="postgres",
        password="mysecretpassword",
        database="postgres",
        host="localhost",
    )
    vector_store = PgVectorStore(client=pool, table_name="my_vector_store444", vector_size=1536)


1. need data base for example as here:
```
sudo docker run --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword -d pgvector/pgvector:pg16
```
2. the data base  DB = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"
3. Create connecrtion_pool
4. and then inittaie the vectre_store
5. Rememeber about vector_size


initiate the pgVector store:
        self._client = client
        self._table_name = table_name
        self._vector_size = vector_size
        self._distance_method = distance_method
        self._hnsw_params = hnsw_params

        client: asyncpg.Pool,
        table_name: str,
        vector_size: int,
        distance_method: str = "cosine",
        hnsw_params: dict | None = None,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
        if hnsw_params is None:
            hnsw_params = {"m": 4, "ef_construction": 10}
        super().__init__(default_options=default_options, metadata_store=metadata_store)
class VectorStoreOptions(Options):
    """
    An object representing the options for the vector store.
    """

    k: int = 5
    max_distance: float | None = None
In the code we have methods:

store     async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the pgVector collection.

        Args:
            entries: The entries to store.
        """
retrieve def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) 
       """
        Retrieves entries from the pgVector collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
list async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    )
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
remove     async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """