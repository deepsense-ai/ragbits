from ragbits.core.config import core_config
from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.llms.litellm import LiteLLM


def get_preferred_llm(llm_type: LLMType = LLMType.TEXT) -> LLM:
    """
    Get an instance of the preferred LLM using the factory function
    specified in the configuration.

    Args:
        llm_type: type of the LLM to get, defaults to text

    Returns:
        LLM: An instance of the preferred LLM.

    """
    factory = core_config.llm_preference_factories[llm_type]
    return LLM.subclass_from_factory(factory)


def simple_litellm_factory() -> LLM:
    """
    A basic LLM factory that creates an LiteLLM instance with the default model,
    default options, and assumes that the API key is set in the environment.

    Returns:
        LLM: An instance of the LiteLLM class.
    """
    return LiteLLM()


def simple_litellm_vision_factory() -> LLM:
    """
    A basic LLM factory that creates an LiteLLM instance with the vision enabled model,
    default options, and assumes that the API key is set in the environment.

    Returns:
        LLM: An instance of the LiteLLM class.
    """
    return LiteLLM(model_name="gpt-4o-mini")


def simple_litellm_structured_output_factory() -> LLM:
    """
    A basic LLM factory that creates an LiteLLM instance with the support for structured output.

    Returns:
        LLM: An instance of the LiteLLM class.
    """
    return LiteLLM(model_name="gpt-4o-mini-2024-07-18", use_structured_output=True)
