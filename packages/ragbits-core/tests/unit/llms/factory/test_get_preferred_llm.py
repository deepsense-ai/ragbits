import pytest

pytest.importorskip("litellm")

from ragbits.core.config import core_config  # noqa: E402
from ragbits.core.llms.base import LLMType  # noqa: E402
from ragbits.core.llms.factory import get_preferred_llm  # noqa: E402
from ragbits.core.llms.litellm import LiteLLM  # noqa: E402


def mock_llm_factory() -> LiteLLM:
    """
    A mock LLM factory that creates a LiteLLM instance with a mock model name.

    Returns:
        LiteLLM: An instance of the LiteLLM.
    """
    return LiteLLM(model_name="mock_model")


def test_get_preferred_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the get_llm_from_factory function.
    """
    monkeypatch.setattr(
        core_config,
        "llm_preference_factories",
        {LLMType.TEXT: "unit.llms.factory.test_get_preferred_llm:mock_llm_factory"},
    )

    llm = get_preferred_llm()
    assert isinstance(llm, LiteLLM)
    assert llm.model_name == "mock_model"
