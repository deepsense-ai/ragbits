"""Tests verifying that google-genai / google-auth are optional deps for VertexAIMultimodalEmbedder."""

from unittest.mock import patch

import pytest


def test_import_dense_embeddings_does_not_raise() -> None:
    """Importing ragbits.core.embeddings.dense must not trigger a google-genai/google-auth import."""
    import ragbits.core.embeddings.dense  # noqa: F401


def test_vertex_embedder_raises_import_error_for_legacy_when_google_auth_missing() -> None:
    """VertexAIMultimodalEmbedder with a legacy model name must raise ImportError when HAS_GOOGLE_AUTH=False."""
    import ragbits.core.embeddings.dense.vertex_multimodal as vertex_module

    with patch.object(vertex_module, "HAS_GOOGLE_AUTH", False):
        from ragbits.core.embeddings.dense.vertex_multimodal import VertexAIMultimodalEmbedder

        with pytest.raises(ImportError, match="ragbits-core\\[vertex\\]"):
            VertexAIMultimodalEmbedder(model_name="multimodalembedding")


def test_vertex_embedder_raises_import_error_for_modern_when_google_genai_missing() -> None:
    """VertexAIMultimodalEmbedder with a modern model name must raise ImportError when HAS_GOOGLE_GENAI=False."""
    import ragbits.core.embeddings.dense.vertex_multimodal as vertex_module

    with patch.object(vertex_module, "HAS_GOOGLE_GENAI", False):
        from ragbits.core.embeddings.dense.vertex_multimodal import VertexAIMultimodalEmbedder

        with pytest.raises(ImportError, match="ragbits-core\\[vertex\\]"):
            VertexAIMultimodalEmbedder(model_name="gemini-embedding-001")


def test_vertex_embedder_resolves_via_getattr_from_dense_package() -> None:
    """'from ragbits.core.embeddings.dense import VertexAIMultimodalEmbedder' resolves via __getattr__."""
    from ragbits.core.embeddings.dense import VertexAIMultimodalEmbedder
    from ragbits.core.embeddings.dense.vertex_multimodal import (
        VertexAIMultimodalEmbedder as DirectVertexEmbedder,
    )

    assert VertexAIMultimodalEmbedder is DirectVertexEmbedder


def test_vertex_embedder_resolves_via_getattr_from_embeddings_package() -> None:
    """'from ragbits.core.embeddings import VertexAIMultimodalEmbedder' resolves via __getattr__."""
    from ragbits.core.embeddings import VertexAIMultimodalEmbedder
    from ragbits.core.embeddings.dense.vertex_multimodal import (
        VertexAIMultimodalEmbedder as DirectVertexEmbedder,
    )

    assert VertexAIMultimodalEmbedder is DirectVertexEmbedder
