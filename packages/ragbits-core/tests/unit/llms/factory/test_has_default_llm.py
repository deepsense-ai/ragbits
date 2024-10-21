from ragbits.core.config import core_config
from ragbits.core.llms.factory import has_default_llm


def test_has_default_llm(monkeypatch):
    """
    Test the has_default_llm function when the default LLM factory is not set.
    """
    monkeypatch.setattr(core_config, "default_llm_factory", None)

    assert has_default_llm() is False


def test_has_default_llm_false(monkeypatch):
    """
    Test the has_default_llm function when the default LLM factory is set.
    """
    monkeypatch.setattr(core_config, "default_llm_factory", "my_project.llms.get_llm")

    assert has_default_llm() is True
