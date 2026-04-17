"""Tests verifying that litellm is an optional dependency for LiteLLM LLM classes."""

from unittest.mock import patch

import pytest


def test_import_ragbits_core_llms_does_not_raise() -> None:
    """Importing ragbits.core.llms must not trigger a litellm import."""
    import ragbits.core.llms  # noqa: F401


def test_litellm_instantiation_raises_import_error_when_missing() -> None:
    """LiteLLM() must raise ImportError containing 'ragbits-core[litellm]' when HAS_LITELLM=False."""
    import ragbits.core.llms.litellm as litellm_module

    with patch.object(litellm_module, "HAS_LITELLM", False):
        from ragbits.core.llms.litellm import LiteLLM

        with pytest.raises(ImportError, match="ragbits-core\\[litellm\\]"):
            LiteLLM()


def test_litellm_instantiation_succeeds_when_present() -> None:
    """LiteLLM('gpt-3.5-turbo') must construct without error when HAS_LITELLM=True."""
    import ragbits.core.llms.litellm as litellm_module

    with patch.object(litellm_module, "HAS_LITELLM", True):
        from ragbits.core.llms.litellm import LiteLLM

        instance = LiteLLM("gpt-3.5-turbo")
        assert instance.model_name == "gpt-3.5-turbo"


def test_litellm_resolves_via_getattr_from_llms_package() -> None:
    """'from ragbits.core.llms import LiteLLM' must resolve via __getattr__ to the correct class."""
    import ragbits.core.llms as llms_module

    llms_module.__dict__.pop("LiteLLM", None)

    from ragbits.core.llms import LiteLLM
    from ragbits.core.llms.litellm import LiteLLM as DirectLiteLLM

    assert LiteLLM is DirectLiteLLM


def test_factory_does_not_import_litellm_at_module_level() -> None:
    """The factory module must NOT have LiteLLM in its namespace at import time."""
    import ragbits.core.llms.factory as factory_module

    assert "LiteLLM" not in factory_module.__dict__


def test_simple_litellm_factory_returns_litellm_instance() -> None:
    """simple_litellm_factory() must resolve LiteLLM lazily and return an instance."""
    import ragbits.core.llms.factory as factory_module
    from ragbits.core.llms.litellm import LiteLLM

    llm = factory_module.simple_litellm_factory()
    assert isinstance(llm, LiteLLM)


def test_simple_litellm_vision_factory_uses_vision_model() -> None:
    """simple_litellm_vision_factory() must return a LiteLLM with a vision-capable model."""
    import ragbits.core.llms.factory as factory_module

    llm = factory_module.simple_litellm_vision_factory()
    assert llm.model_name == "gpt-4o-mini"


def test_simple_litellm_structured_output_factory_enables_structured_output() -> None:
    """simple_litellm_structured_output_factory() must set use_structured_output=True."""
    import ragbits.core.llms.factory as factory_module

    llm = factory_module.simple_litellm_structured_output_factory()
    assert llm.use_structured_output is True
