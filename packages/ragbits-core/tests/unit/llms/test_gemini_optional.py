"""Tests verifying that the 'google-genai' package is an optional dependency for GeminiLLM."""

from unittest.mock import patch

import pytest


def test_import_ragbits_core_llms_does_not_raise() -> None:
    """Importing ragbits.core.llms must not trigger a google-genai import."""
    import ragbits.core.llms  # noqa: F401


def test_gemini_llm_raises_import_error_when_missing() -> None:
    """GeminiLLM() must raise ImportError containing 'ragbits-core[gemini]' when HAS_GOOGLE_GENAI=False."""
    import ragbits.core.llms.gemini as gemini_module

    with patch.object(gemini_module, "HAS_GOOGLE_GENAI", False):
        from ragbits.core.llms.gemini import GeminiLLM

        with pytest.raises(ImportError, match="ragbits-core\\[gemini\\]"):
            GeminiLLM()


def test_gemini_llm_resolves_via_getattr_from_llms_package() -> None:
    """'from ragbits.core.llms import GeminiLLM' must resolve via __getattr__ to the correct class."""
    from ragbits.core.llms import GeminiLLM
    from ragbits.core.llms.gemini import GeminiLLM as DirectGeminiLLM

    assert GeminiLLM is DirectGeminiLLM
