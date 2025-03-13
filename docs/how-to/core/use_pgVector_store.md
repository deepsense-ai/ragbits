# How to use pgVector database with Ragbits

## How to set up pgVector database locally
To run a local instance of pgVector, use Docker to pull and start the database container.

1. **Pull the pgVector Docker image**
`bash sudo docker pull pgvector/pgvector:pg17`


2. **Run the PostgreSQL container with pgVector**

```bash
    docker run --name postgres_container \
            -p 5432:5432 \
            -e POSTGRES_USER=ragbits_user \
            -e POSTGRES_PASSWORD=ragbits_password \
            -e POSTGRES_DB = ragbits_db \
            -d pgvector/pgvector:0.8.0-pg17
```
    * `--name` the docker container a name assign to postgres.

    * `-p` 5432:5432 maps the default PostgreSQL port to the local machine.

    * `-e` POSTGRES_USER=ragbits_user sets the user name of the database

    * `-e` POSTGRES_PASSWORD=ragbits_password example sets the database password.

    * `-d` runs the container in detached mode.

The local instance of pgVector is accessible using the following connection string:
```DB = "postgresql://ragbits_user:ragbits_password@localhost:5432/ragbits_db"```

The database connection string (DB) may vary depending on the deployment setup.
If the database is hosted remotely, in the cloud, or configured differently,
update the connection string accordingly to match the appropriate host, port, credentials, and database name.

## How to connect to pgVector database with Ragbits
To connect to PostgreSQL, establish a connection pool using asyncpg library.

The connection string can be provided directly:
```python
import asyncpg
DB = "postgresql://ragbits_user:ragbits_password@localhost:5432/ragbits_db"
async def main() -> None:
    pool = await asyncpg.create_pool(dsn=DB)
```
Or specified using individual parameters:
```python
import asyncpg
async def main() -> None:
    pool = await asyncpg.create_pool(
        user="ragbits_user",
        password="ragbits_password",
        database="ragbits_db",
        host="localhost",
    )
```
To ensure proper resource management, you can use asyncpg.create_pool as a context manager:
```python
import asyncpg
DB = "postgresql://ragbits_user:ragbits_password@localhost:5432/ragbits_db"
async with asyncpg.create_pool(dsn=DB) as pool:

```

The connection pool created with asyncpg.create_pool will be used to initialize an instance of PgVectorStore.


```python
import asyncpg
from ragbits.core.vector_stores.pgvector import PgVectorStore
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
async def main() -> None:
  DB = "postgresql://ragbits_user:ragbits_password@localhost:5432/ragbits_db"
  async with asyncpg.create_pool(dsn=DB) as pool:
    embedder = LiteLLMEmbedder(model="text-embedding-3-small")
    vector_store = PgVectorStore(embedder=embedder, client=pool, table_name="test_table", vector_size=1536)
```

**Note**: Ensure that the vector size is correctly configured when initializing PgVectorStore,
as it must match the expected dimensions of the stored embeddings.

## pgVectorStore in Ragbits
Example:
```python
import asyncpg
import asyncio
from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.core.vector_stores.pgvector import PgVectorStore
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
async def main() -> None:
  DB = "postgresql://ragbits_user:ragbits_password@localhost:5432/ragbits_db"
  async with asyncpg.create_pool(dsn=DB) as pool:
    embedder = LiteLLMEmbedder(model="text-embedding-3-small")
    vector_store = PgVectorStore(embedder=embedder, client=pool, table_name="test_table", vector_size=3)
    data = [VectorStoreEntry(id="test_id_1", key="test_key_1", vector=[0.1, 0.2, 0.3],
            metadata={"key1": "value1", "content": "test 1"}),
            VectorStoreEntry(id="test_id_2", key="test_key_2", vector=[0.4, 0.5, 0.6],
                              metadata={"key2": "value2", "content": "test 2"})]

    await vector_store.store(data)
    all_entries = await vector_store.list()
    print("All entries ", all_entries)
    list_result = await vector_store.list({"content": "test 1"})
    print("Entries with  {content: test 1}", list_result)
    retrieve_result = await vector_store.retrieve(vector=[0.39, 0.55, 0.6])
    print("Entries similar to [0.17, 0.23, 0.314] ", retrieve_result)
    await vector_store.remove(["test_id_1", "test_id_2"])
    after_remove = await vector_store.list()
    print("Entries after remove ", after_remove)

if __name__ == "__main__":
    asyncio.run(main())
```

### PgVectorStore distance

One of the PgVectorStore parameters is distance_method - the similarity metric used for vector comparisons.
Supported values include:

 * "cosine" (<=>) – Cosine distance
 * "l2" (<->) – Euclidean (L2) distance
 *   - "l1" (<+>) – Manhattan (L1) distance
 *  - "ip" (<#>) – Inner product
 *   - "bit_hamming" (<~>) – Hamming distance
 *   - "bit_jaccard" (<%>) – Jaccard distance
 *   - "sparsevec_l2" (<->) – Sparse vector L2 distance
 *   - "halfvec_l2" (<->) – Half precision vector L2 distance

The default value for distance method is cosine similarity.




