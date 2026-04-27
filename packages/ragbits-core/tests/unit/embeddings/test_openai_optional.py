"""Tests verifying that the 'openai' package is an optional dependency for OpenAIEmbedder."""

from unittest.mock import patch

import pytest


def test_import_dense_embeddings_does_not_raise() -> None:
    """Importing ragbits.core.embeddings.dense must not trigger an openai import."""
    import ragbits.core.embeddings.dense  # noqa: F401


def test_openai_embedder_raises_import_error_when_missing() -> None:
    """OpenAIEmbedder() must raise ImportError containing 'ragbits-core[openai]' when HAS_OPENAI=False."""
    import ragbits.core.embeddings.dense.openai as openai_module

    with patch.object(openai_module, "HAS_OPENAI", False):
        from ragbits.core.embeddings.dense.openai import OpenAIEmbedder

        with pytest.raises(ImportError, match="ragbits-core\\[openai\\]"):
            OpenAIEmbedder()


def test_openai_embedder_resolves_via_getattr_from_dense_package() -> None:
    """'from ragbits.core.embeddings.dense import OpenAIEmbedder' must resolve via __getattr__."""
    from ragbits.core.embeddings.dense import OpenAIEmbedder
    from ragbits.core.embeddings.dense.openai import OpenAIEmbedder as DirectOpenAIEmbedder

    assert OpenAIEmbedder is DirectOpenAIEmbedder


def test_openai_embedder_resolves_via_getattr_from_embeddings_package() -> None:
    """'from ragbits.core.embeddings import OpenAIEmbedder' must resolve via __getattr__."""
    from ragbits.core.embeddings import OpenAIEmbedder
    from ragbits.core.embeddings.dense.openai import OpenAIEmbedder as DirectOpenAIEmbedder

    assert OpenAIEmbedder is DirectOpenAIEmbedder
