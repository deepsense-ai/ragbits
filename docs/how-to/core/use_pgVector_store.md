# How to use pgVector database with Ragbits

## How to set up pgVector database locally
To run a local instance of pgVector, use Docker to pull and start the database container.

1. **Pull the pgVector Docker image**
```bash
sudo docker pull pgvector/pgvector:pg17
 ```

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

### PgVectorStore Parameters

The PgVectorStore class is initialized with the following parameters:

* embedder: Embedder - An instance of Embedder class responsible for converting entries to vectors.
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
* embedding_name_text - the name of embeddings for text
* embedding_name_image - the name of embeddings for images

**Note**: Currently, pgVector vector store doesn't support images.

### VectorStoreEntry

Entries stored in the database are represented by the VectorStoreEntry class, which consists of:

* id: UUID – A unique identifier for the entry.
* text: str – A text data
* image_bytes: SerializableBytes - An image data.
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
retrieve(vector: list[float], options: VectorStoreOptions) -> list[VectorStoreResult]

Finds entries similar to the provided query vector based on the configured distance metric.

* vector: list[float] – The query vector.
* options: VectorStoreOptions – Query options, including:
     - k – Number of nearest neighbors to return.
     - max_distance – Maximum allowable distance for retrieval.
   The retrieve method searches for the closest entries using the specified distance metric defined in the table
   and applies the max_distance constraint from VectorStoreOptions.
  * Returns the list of VectorStoreResult, an object consists of:
     - entry: VectorStoreEntry - An entry in database.
     - vectors: dict[str, list[float]]  - the vector for given embedding type.
     - score: float - similarity score between given query vector and query result vector.