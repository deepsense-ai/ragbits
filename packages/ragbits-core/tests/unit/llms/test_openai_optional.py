"""Tests verifying that the 'openai' package is an optional dependency for OpenAILLM."""

from unittest.mock import patch

import pytest


def test_import_ragbits_core_llms_does_not_raise() -> None:
    """Importing ragbits.core.llms must not trigger an openai import."""
    import ragbits.core.llms  # noqa: F401


def test_openai_llm_raises_import_error_when_missing() -> None:
    """OpenAILLM() must raise ImportError containing 'ragbits-core[openai]' when HAS_OPENAI=False."""
    import ragbits.core.llms.openai as openai_module

    with patch.object(openai_module, "HAS_OPENAI", False):
        from ragbits.core.llms.openai import OpenAILLM

        with pytest.raises(ImportError, match="ragbits-core\\[openai\\]"):
            OpenAILLM()


def test_openai_llm_resolves_via_getattr_from_llms_package() -> None:
    """'from ragbits.core.llms import OpenAILLM' must resolve via __getattr__ to the correct class."""
    import ragbits.core.llms as llms_module

    llms_module.__dict__.pop("OpenAILLM", None)

    from ragbits.core.llms import OpenAILLM
    from ragbits.core.llms.openai import OpenAILLM as DirectOpenAILLM

    assert OpenAILLM is DirectOpenAILLM
