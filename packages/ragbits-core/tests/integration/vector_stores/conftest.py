from collections.abc import AsyncGenerator

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.weaviate import WeaviateContainer

POSTGRES_IMAGE = "pgvector/pgvector:pg17"
WEAVIATE_IMAGE = "cr.weaviate.io/semitechnologies/weaviate:1.30.6"


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(POSTGRES_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def weaviate_container():
    with WeaviateContainer(WEAVIATE_IMAGE) as container:
        yield container


@pytest.fixture(name="pgvector_test_db")
async def pgvector_test_db_fixture(postgres_container: PostgresContainer) -> AsyncGenerator[asyncpg.Pool, None]:
    dsn = (
        f"postgresql://{postgres_container.username}:{postgres_container.password}"
        f"@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}"
        f"/{postgres_container.dbname}"
    )

    async with asyncpg.create_pool(dsn) as pool:
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        async with pool.acquire() as conn, conn.transaction():
            await conn.execute("DROP SCHEMA public CASCADE;")
            await conn.execute("CREATE SCHEMA public;")

        yield pool
