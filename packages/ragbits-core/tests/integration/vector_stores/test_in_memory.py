import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta


async def test_update_document() -> None:
    document_1_content = "This is a test sentence and it should be in the vector store"
    document_2_content = "This is another test sentence and it should be removed from the vector store"
    document_2_new_content = "This is one more test sentence and it should be added to the vector store"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as file_1:
        file_1.write(document_1_content)
        document_1_path = file_1.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as file_2:
        file_2.write(document_2_content)
        document_2_path = file_2.name

    document_1 = DocumentMeta.from_local_path(Path(document_1_path))
    document_2 = DocumentMeta.from_local_path(Path(document_2_path))

    embedder = AsyncMock()
    embedder.embed_text.return_value = [[0.0], [0.0]]
    vector_store = InMemoryVectorStore()
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )
    await document_search.ingest([document_1, document_2])

    with open(document_2_path, "w") as file:
        file.write(document_2_new_content)

    await document_search.ingest([document_2])

    os.remove(document_1_path)
    os.remove(document_2_path)

    document_1_present = False
    document_2_old_present = False
    document_2_new_present = False
    for entry in await vector_store.list():
        if entry.key == document_1_content:
            document_1_present = True
        elif entry.key == document_2_content:
            document_2_old_present = True
        elif entry.key == document_2_new_content:
            document_2_new_present = True
    assert document_1_present
    assert document_2_new_present
    assert not document_2_old_present
