"""Tests verifying that the 'google-genai' package is an optional dependency for GeminiEmbedder."""

from unittest.mock import patch

import pytest


def test_import_dense_embeddings_does_not_raise() -> None:
    """Importing ragbits.core.embeddings.dense must not trigger a google-genai import."""
    import ragbits.core.embeddings.dense  # noqa: F401


def test_gemini_embedder_raises_import_error_when_missing() -> None:
    """GeminiEmbedder() must raise ImportError containing 'ragbits-core[gemini]' when HAS_GEMINI=False."""
    import ragbits.core.embeddings.dense.gemini as gemini_module

    with patch.object(gemini_module, "HAS_GEMINI", False):
        from ragbits.core.embeddings.dense.gemini import GeminiEmbedder

        with pytest.raises(ImportError, match="ragbits-core\\[gemini\\]"):
            GeminiEmbedder()


def test_gemini_embedder_resolves_via_getattr_from_dense_package() -> None:
    """'from ragbits.core.embeddings.dense import GeminiEmbedder' must resolve via __getattr__."""
    import ragbits.core.embeddings.dense as dense_module

    dense_module.__dict__.pop("GeminiEmbedder", None)

    from ragbits.core.embeddings.dense import GeminiEmbedder
    from ragbits.core.embeddings.dense.gemini import GeminiEmbedder as DirectGeminiEmbedder

    assert GeminiEmbedder is DirectGeminiEmbedder


def test_gemini_embedder_resolves_via_getattr_from_embeddings_package() -> None:
    """'from ragbits.core.embeddings import GeminiEmbedder' must resolve via __getattr__."""
    import ragbits.core.embeddings as embeddings_module

    embeddings_module.__dict__.pop("GeminiEmbedder", None)

    from ragbits.core.embeddings import GeminiEmbedder
    from ragbits.core.embeddings.dense.gemini import GeminiEmbedder as DirectGeminiEmbedder

    assert GeminiEmbedder is DirectGeminiEmbedder
