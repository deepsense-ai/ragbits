import sys

from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.llm import LLMQueryRephraser
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompts import QueryRephraserInput, QueryRephraserPrompt

__all__ = [
    "LLMQueryRephraser",
    "NoopQueryRephraser",
    "QueryRephraser",
    "QueryRephraserInput",
    "QueryRephraserPrompt",
    "get_rephraser",
]

module = sys.modules[__name__]


def get_rephraser(config: dict | None = None) -> QueryRephraser:
    """
    Initializes and returns a QueryRephraser object based on the provided configuration.

    Args:
        config: A dictionary containing configuration details for the QueryRephraser.

    Returns:
        An instance of the specified QueryRephraser class, initialized with the provided config
        (if any) or default arguments.

    Raises:
        KeyError: If the configuration dictionary does not contain a "type" key.
        ValueError: If an invalid rephraser class is specified in the configuration.
    """
    if config is None:
        return NoopQueryRephraser()

    rephraser_cls = get_cls_from_config(config["type"], module)

    if not issubclass(rephraser_cls, QueryRephraser):
        raise ValueError(f"Invalid rephraser class: {rephraser_cls}")

    return rephraser_cls.from_config(config.get("config", {}))
