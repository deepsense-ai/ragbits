from uuid import UUID

import pytest

from ragbits.core.vector_stores.base import VectorStoreEntry


async def test_unserializable_metadata_raises_error() -> None:
    with pytest.raises(ValueError, match="Metadata must be JSON serializable."):
        VectorStoreEntry(
            id=UUID("48183d3f-61c6-4ef3-bf62-e45d9389acee"),
            text="test",
            metadata={"anoterh": [1, 2, 3], "unsupported_type": object()},
        )
