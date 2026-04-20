"""Tests verifying that the 'anthropic' package is an optional dependency for AnthropicLLM."""

from unittest.mock import patch

import pytest


def test_import_ragbits_core_llms_does_not_raise() -> None:
    """Importing ragbits.core.llms must not trigger an anthropic import."""
    import ragbits.core.llms  # noqa: F401


def test_anthropic_llm_raises_import_error_when_missing() -> None:
    """AnthropicLLM() must raise ImportError containing 'ragbits-core[anthropic]' when HAS_ANTHROPIC=False."""
    import ragbits.core.llms.anthropic as anthropic_module

    with patch.object(anthropic_module, "HAS_ANTHROPIC", False):
        from ragbits.core.llms.anthropic import AnthropicLLM

        with pytest.raises(ImportError, match="ragbits-core\\[anthropic\\]"):
            AnthropicLLM()


def test_anthropic_llm_resolves_via_getattr_from_llms_package() -> None:
    """'from ragbits.core.llms import AnthropicLLM' must resolve via __getattr__ to the correct class."""
    from ragbits.core.llms import AnthropicLLM
    from ragbits.core.llms.anthropic import AnthropicLLM as DirectAnthropicLLM

    assert AnthropicLLM is DirectAnthropicLLM
