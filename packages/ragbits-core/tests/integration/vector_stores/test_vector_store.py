from unittest.mock import AsyncMock

import pytest
from chromadb import EphemeralClient
from qdrant_client import AsyncQdrantClient

from ragbits.core.vector_stores.base import VectorStore
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.sources import LocalFileSource


@pytest.mark.parametrize(
    "vector_store",
    [
        InMemoryVectorStore(),
        ChromaVectorStore(
            client=EphemeralClient(),
            index_name="test_index_name",
        ),
        QdrantVectorStore(
            client=AsyncQdrantClient(":memory:"),
            index_name="test_index_name",
        ),
    ],
)
async def test_handling_document_ingestion_with_different_content_and_verifying_replacement(
    vector_store: VectorStore,
) -> None:
    document_1_content = "This is a test sentence and it should be in the vector store"
    document_2_content = "This is another test sentence and it should be removed from the vector store"
    document_2_new_content = "This is one more test sentence and it should be added to the vector store"

    document_1 = DocumentMeta.create_text_document_from_literal(document_1_content)
    document_2 = DocumentMeta.create_text_document_from_literal(document_2_content)

    embedder = AsyncMock()
    embedder.embed_text.return_value = [[0.0], [0.0]]
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )
    await document_search.ingest([document_1, document_2])

    if isinstance(document_2.source, LocalFileSource):
        document_2_path = document_2.source.path
    with open(document_2_path, "w") as file:
        file.write(document_2_new_content)

    await document_search.ingest([document_2])

    document_contents = {entry.key for entry in await vector_store.list()}

    assert document_1_content in document_contents
    assert document_2_new_content in document_contents
    assert document_2_content not in document_contents
