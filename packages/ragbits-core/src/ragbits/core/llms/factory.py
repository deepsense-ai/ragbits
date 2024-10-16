import importlib

from ragbits.core.config import core_config
from ragbits.core.llms.base import LLM
from ragbits.core.llms.litellm import LiteLLM


def get_llm_from_factory(factory_path: str) -> LLM:
    """
    Get an instance of an LLM using a factory function specified by the user.

    Args:
        factory_path (str): The path to the factory function.

    Returns:
        LLM: An instance of the LLM.
    """
    module_name, function_name = factory_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    return function()


def has_default_llm() -> bool:
    """
    Check if the default LLM factory is set in the configuration.

    Returns:
        bool: Whether the default LLM factory is set.
    """
    return core_config.default_llm_factory is not None


def get_default_llm() -> LLM:
    """
    Get an instance of the default LLM using the factory function
    specified in the configuration.

    Returns:
        LLM: An instance of the default LLM.

    Raises:
        ValueError: If the default LLM factory is not set.
    """
    factory = core_config.default_llm_factory
    if factory is None:
        raise ValueError("Default LLM factory is not set")

    return get_llm_from_factory(factory)


def simple_litellm_factory() -> LLM:
    """
    A basic LLM factory that creates an LiteLLM instance with the default model,
    default options, and assumes that the API key is set in the environment.

    Returns:
        LLM: An instance of the LiteLLM.
    """
    return LiteLLM()
