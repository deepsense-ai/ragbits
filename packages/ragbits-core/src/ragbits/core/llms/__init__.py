import sys

from .base import LLM
from .litellm import LiteLLM
from .local import LocalLLM

__all__ = ["LLM", "LiteLLM", "LocalLLM"]


module = sys.modules[__name__]


def get_llm(config: dict) -> LLM:
    """
    Initializes and returns an LLM object based on the provided configuration.

    Args:
        config : A dictionary containing configuration details for the LLM.

    Returns:
        An instance of the specified LLM class, initialized with the provided config
        (if any) or default arguments.

    Raises:
        KeyError: If the configuration dictionary does not contain a "type" key.
        ValueError: If the LLM class is not a subclass of LLM.
    """
    llm_type = config["type"]
    llm_config = config.get("config", {})
    default_options = llm_config.pop("default_options", None)

    llm_cls = getattr(module, llm_type)

    if not issubclass(llm_cls, LLM):
        raise ValueError(f"Invalid LLM class: {llm_cls}")

    # We need to infer the options class from the LLM class.
    # pylint: disable=protected-access
    options = llm_cls._options_cls(**default_options) if default_options else None  # type: ignore

    return llm_cls(**llm_config, default_options=options)
