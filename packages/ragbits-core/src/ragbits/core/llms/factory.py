import importlib

from ragbits.core.config import core_config
from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.llms.litellm import LiteLLM


def get_llm_from_factory(factory_path: str) -> LLM:
    """
    Get an instance of an LLM using a factory function specified by the user.

    Args:
        factory_path (str): The path to the factory function.

    Returns:
        LLM: An instance of the LLM class.
    """
    module_name, function_name = factory_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    return function()


def get_default_llm(llm_type: LLMType = LLMType.TEXT) -> LLM:
    """
    Get an instance of the default LLM using the factory function
    specified in the configuration.

    Args:
        llm_type: type of the LLM to get, defaults to text

    Returns:
        LLM: An instance of the default LLM.

    Raises:
        ValueError: If the expected llm type is not defined in config
    """
    if llm_type not in core_config.default_llm_factories:
        raise ValueError(f"Default LLM of type {llm_type} is not defined in pyproject.toml config.")
    factory = core_config.default_llm_factories[llm_type]
    return get_llm_from_factory(factory)


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
