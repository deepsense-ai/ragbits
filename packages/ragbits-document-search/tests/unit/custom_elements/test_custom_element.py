from unittest.mock import AsyncMock
from uuid import UUID

import pytest

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
                    "element_type": "custom_element",
                    "document_meta": {
                        "document_type": "txt",
                        "source": {
                            "path": "/path/to/file.txt",
                            "source_type": "local_file_source",
                            "id": "file:/path/to/file.txt",
                        },
                    },
                    "custom_field": "Sample value",
                },
            ),
            score=0.95,
            vector=[0.1, 0.2, 0.3],
        ),
    ]
    mock_store.retrieve.return_value = sample_documents
    return mock_store


async def test_document_search_fails_with_custom_element_without_module_import(mock_vector_store: AsyncMock):
    document_search = DocumentSearch(vector_store=mock_vector_store)

    with pytest.raises(KeyError, match="custom_element"):
        await document_search.search(
            query="Sample query",
        )


async def test_document_search_succeeds_with_custom_element_with_module_import(mock_vector_store: AsyncMock):
    core_config = get_config_instance(CoreConfig)
    core_config.modules_to_import = ["custom_element"]
    import_modules_from_config(core_config)

    document_search = DocumentSearch(vector_store=mock_vector_store)
    query = "Sample query"
    results = await document_search.search(
        query=query,
    )

    mock_vector_store.retrieve.assert_called_once_with(
        text=query, options=VectorStoreOptions(k=5, score_threshold=None)
    )
    assert results[0].text_representation == "Sample value"

    from custom_element import CustomElement

    assert isinstance(results[0], CustomElement)
