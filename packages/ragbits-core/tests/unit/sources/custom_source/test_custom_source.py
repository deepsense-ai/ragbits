from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from ragbits.core.config import CoreConfig, import_modules_from_config
from ragbits.core.utils._pyproject import get_config_instance
from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreOptions, VectorStoreResult
from ragbits.document_search import DocumentSearch


@pytest.fixture
def mock_vector_store():
    mock_store = AsyncMock()
    sample_documents = [
        VectorStoreResult(
            entry=VectorStoreEntry(
                id=UUID("015fd451-1a2a-4386-a3ab-c20f631d7fbf"),
                text="Entry 1",
                image_bytes=None,
                metadata={
                    "element_type": "text",
                    "document_meta": {
                        "document_type": "txt",
                        "source": {
                            "path": "/path/to/file.txt",
                            "source_type": "custom_source",
                            "id": "cs:/path/to/file.txt",
                        },
                    },
                    "content": "Sample text",
                    "text_representation": "Sample text",
                },
            ),
            score=0.95,
            vector=[0.1, 0.2, 0.3],
        ),
    ]
    mock_store.retrieve.return_value = sample_documents
    return mock_store


async def test_document_search_fails_with_custom_source_without_module_import(mock_vector_store: AsyncMock):
    document_search = DocumentSearch(vector_store=mock_vector_store)

    with pytest.raises(ValidationError):
        await document_search.search(
            query="Sample query",
        )


async def test_document_search_succeeds_with_custom_source_with_module_import(mock_vector_store: AsyncMock):
    core_config = get_config_instance(CoreConfig)
    core_config.modules_to_import = ["custom_source"]
    import_modules_from_config(core_config)

    document_search = DocumentSearch(vector_store=mock_vector_store)

    query = "Sample query"
    results = await document_search.search(
        query=query,
    )

    mock_vector_store.retrieve.assert_called_once_with(
        text=query, options=VectorStoreOptions(k=5, score_threshold=None)
    )
    assert results[0].text_representation == "Sample text"

    from custom_source import CustomSource

    assert isinstance(results[0].document_meta.source, CustomSource)
