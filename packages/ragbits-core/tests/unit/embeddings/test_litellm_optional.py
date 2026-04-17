"""Tests verifying that litellm is an optional dependency for LiteLLMEmbedder."""

from unittest.mock import patch

import pytest


def test_import_dense_embeddings_does_not_raise() -> None:
    """Importing ragbits.core.embeddings.dense must not trigger a litellm import."""
    import ragbits.core.embeddings.dense  # noqa: F401


def test_litellm_embedder_raises_import_error_when_missing() -> None:
    """LiteLLMEmbedder() must raise ImportError containing 'ragbits-core[litellm]' when HAS_LITELLM=False."""
    import ragbits.core.embeddings.dense.litellm as litellm_module

    with patch.object(litellm_module, "HAS_LITELLM", False):
        from ragbits.core.embeddings.dense.litellm import LiteLLMEmbedder

        with pytest.raises(ImportError, match="ragbits-core\\[litellm\\]"):
            LiteLLMEmbedder()


def test_litellm_embedder_constructs_when_present() -> None:
    """LiteLLMEmbedder('text-embedding-3-small') must construct without error when HAS_LITELLM=True."""
    import ragbits.core.embeddings.dense.litellm as litellm_module

    with patch.object(litellm_module, "HAS_LITELLM", True):
        from ragbits.core.embeddings.dense.litellm import LiteLLMEmbedder

        embedder = LiteLLMEmbedder("text-embedding-3-small")
        assert embedder.model_name == "text-embedding-3-small"


def test_litellm_embedder_resolves_via_getattr_from_dense_package() -> None:
    """'from ragbits.core.embeddings.dense import LiteLLMEmbedder' must resolve via __getattr__."""
    import ragbits.core.embeddings.dense as dense_module

    dense_module.__dict__.pop("LiteLLMEmbedder", None)

    from ragbits.core.embeddings.dense import LiteLLMEmbedder
    from ragbits.core.embeddings.dense.litellm import LiteLLMEmbedder as DirectLiteLLMEmbedder

    assert LiteLLMEmbedder is DirectLiteLLMEmbedder


def test_litellm_embedder_resolves_via_getattr_from_embeddings_package() -> None:
    """'from ragbits.core.embeddings import LiteLLMEmbedder' must resolve via __getattr__."""
    import ragbits.core.embeddings as embeddings_module

    embeddings_module.__dict__.pop("LiteLLMEmbedder", None)

    from ragbits.core.embeddings import LiteLLMEmbedder
    from ragbits.core.embeddings.dense.litellm import LiteLLMEmbedder as DirectLiteLLMEmbedder

    assert LiteLLMEmbedder is DirectLiteLLMEmbedder
