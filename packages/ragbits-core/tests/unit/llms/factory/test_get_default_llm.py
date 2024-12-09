import pytest

from ragbits.core.config import core_config
from ragbits.core.llms.base import LLMType
from ragbits.core.llms.factory import get_default_llm
from ragbits.core.llms.litellm import LiteLLM


def mock_llm_factory() -> LiteLLM:
    """
    A mock LLM factory that creates a LiteLLM instance with a mock model name.

    Returns:
        LiteLLM: An instance of the LiteLLM.
    """
    return LiteLLM(model_name="mock_model")


def test_get_default_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the get_llm_from_factory function.
    """
    monkeypatch.setattr(
        core_config, "default_llm_factories", {LLMType.TEXT: "unit.llms.factory.test_get_default_llm:mock_llm_factory"}
    )

    llm = get_default_llm()
    assert isinstance(llm, LiteLLM)
    assert llm.model_name == "mock_model"
