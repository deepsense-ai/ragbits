import sys

from .base import LLM
from .litellm import LiteLLM
from .local import LocalLLM

__all__ = ["LLM", "LiteLLM", "LocalLLM"]


module = sys.modules[__name__]


def get_llm(llm_config: dict) -> LLM:
    """
    Initializes and returns an LLM object based on the provided LLM configuration.

    Args:
        llm_config : A dictionary containing configuration details for the LLM.

    Returns:
        An instance of the specified LLM class, initialized with the provided config
        (if any) or default arguments.
    """
    llm_type = llm_config["type"]
    config = llm_config.get("config", {})

    return getattr(module, llm_type)(**config)
