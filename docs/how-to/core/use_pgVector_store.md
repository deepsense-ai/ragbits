# How to use pgVector database with Ragbits

## How to set up pgVector database locally
To run a local instance of pgVector, use Docker to pull and start the database container.

1. **Pull the pgVector Docker image**
```bash
sudo docker pull pgvector/pgvector:pg16
 ```

2. **Run the PostgreSQL container with pgVector**
```bash
sudo docker run --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=mysecretpassword -d pgvector/pgvector:pg16
```
    * `--name` postgres assigns the container a name (postgres).
    * `-p` 5432:5432 maps the default PostgreSQL port to the local machine.
    * `-e` POSTGRES_PASSWORD=mysecretpassword sets the database password.
    * `-d` runs the container in detached mode.

The local instance of pgVector is accessible using the following connection string:
```DB = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"```

The database connection string (DB) may vary depending on the deployment setup.
If the database is hosted remotely, in the cloud, or configured differently,
update the connection string accordingly to match the appropriate host, port, credentials, and database name.

## How to connect to pgVector database with Ragbits
To connect to PostgreSQL, establish a connection pool using asyncpg.
The connection string can be provided directly or specified using individual parameters.

```python
import asyncpg
from ragbits.core.vector_stores.pgvector import PgVectorStore
DB = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"
async def main() -> None:
    pool = await asyncpg.create_pool(DB)
    vector_store = PgVectorStore(client=pool, table_name="test_table", vector_size=1536)
```
Alternatively, the connection pool can be created explicitly:
```python
import asyncpg
from ragbits.core.vector_stores.pgvector import PgVectorStore
async def main() -> None:
    pool = await asyncpg.create_pool(
        user="postgres",
        password="mysecretpassword",
        database="postgres",
        host="localhost",
    )
    vector_store = PgVectorStore(client=pool, table_name="test_table", vector_size=1536)
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

DB = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"

async def main() -> None:
    pool = await asyncpg.create_pool(DB)
    vector_store = PgVectorStore(client=pool, table_name="test_tableZXXX", vector_size=3)
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
### PgVectorStore Parameters
The PgVectorStore class is initialized with the following parameters:

* client: asyncpg.Pool – An instance of asyncpg.Pool used for database connections.
* table_name: str – The name of the table where vectors are stored.
* vector_size: int – The dimensionality of the vectors. This must match the stored embeddings.
* distance_method: str (default: `"cosine"") – The similarity metric used for vector comparisons.
Supported values include:
    - "cosine" (<=>) – Cosine distance
    - "l2" (<->) – Euclidean (L2) distance
    - "l1" (<+>) – Manhattan (L1) distance
    - "ip" (<#>) – Inner product
    - "bit_hamming" (<~>) – Hamming distance
    - "bit_jaccard" (<%>) – Jaccard distance
    - "sparsevec_l2" (<->) – Sparse vector L2 distance
    - "halfvec_l2" (<->) – Half precision vector L2 distance
* hnsw_params: dict | None (default: {"m": 4, "ef_construction": 10}) – HNSW indexing parameters.
If not specified, the default values are used.
* default_options: VectorStoreOptions | None (default: VectorStoreOptions(k=5, max_distance=None)) –
Default search options, including:
    - k: int = 5 – Number of nearest neighbors to retrieve.
    - max_distance: float | None = None – Maximum distance threshold for retrieval.
* metadata_store: MetadataStore | None – An optional metadata store for additional data management.

### VectoreStoreEntry
Entries stored in the database are represented by the VectorStoreEntry class, which consists of:

* id: str – A unique identifier for the entry.
* key: str – A key associated with the vector.
* vector: list[float] – The vector representation of the entry.
* metadata: dict – Additional metadata associated with the entry.

### pgVectorStore methods
The PgVectorStore class provides the following methods for managing and querying vector data:

#### store
store(entries: list[VectorStoreEntry]) -> None
Stores a list of VectorStoreEntry objects in the database.
Each entry consists of an ID, key, vector, and optional metadata.
#### remove
remove(ids: list[str]) -> None
Removes entries from the database based on a list of entry IDs.
#### list
list(where: dict, limit: int | None = None, offset: int | None = None) -> list[VectorStoreEntry]

Retrieves a list of entries that match the specified metadata filter.

* where: dict – A dictionary specifying metadata conditions for filtering entries.
* limit: int | None – The maximum number of entries to return (default is unlimited).
* offset: int | None – The number of entries to skip before returning results (default is 0).

#### retrieve
retrieve(vector: list[float], options: VectorStoreOptions) -> list[VectorStoreEntry]

Finds entries similar to the provided query vector based on the configured distance metric.

* vector: list[float] – The query vector.
* options: VectorStoreOptions – Query options, including:
     - k – Number of nearest neighbors to return.
     - max_distance – Maximum allowable distance for retrieval.
   The retrieve method searches for the closest entries using the specified distance metric defined in the table
   and applies the max_distance constraint from VectorStoreOptions.