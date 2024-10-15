from ragbits.core.llms.factory import get_llm_from_factory
from ragbits.core.llms.litellm import LiteLLM


def mock_llm_factory() -> LiteLLM:
    """
    A mock LLM factory that creates a LiteLLM instance with a mock model name.

    Returns:
        LiteLLM: An instance of the LiteLLM.
    """
    return LiteLLM(model_name="mock_model")


def test_get_llm_from_factory():
    """
    Test the get_llm_from_factory function.
    """
    llm = get_llm_from_factory("factory.test_get_llm_from_factory.mock_llm_factory")

    assert isinstance(llm, LiteLLM)
    assert llm.model_name == "mock_model"
