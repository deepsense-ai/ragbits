import pytest

pytest.importorskip("litellm")

from ragbits.core.llms.litellm import LiteLLM  # noqa: E402
from ragbits.core.utils.config_handling import ObjectConstructionConfig  # noqa: E402
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser  # noqa: E402
from ragbits.document_search.retrieval.rephrasers.llm import LLMQueryRephraser, LLMQueryRephraserPrompt  # noqa: E402
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser  # noqa: E402


def test_subclass_from_config():
    config = ObjectConstructionConfig.model_validate(
        {"type": "ragbits.document_search.retrieval.rephrasers:NoopQueryRephraser"}
    )
    rephraser: QueryRephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, NoopQueryRephraser)


def test_subclass_from_config_default_path():
    config = ObjectConstructionConfig.model_validate({"type": "NoopQueryRephraser"})
    rephraser: QueryRephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, NoopQueryRephraser)


def test_subclass_from_config_llm():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rephrasers.llm:LLMQueryRephraser",
            "config": {
                "llm": {
                    "type": "ragbits.core.llms.litellm:LiteLLM",
                    "config": {"model_name": "some_model"},
                },
            },
        }
    )
    rephraser: QueryRephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, LLMQueryRephraser)
    assert isinstance(rephraser._llm, LiteLLM)
    assert rephraser._llm.model_name == "some_model"


def test_subclass_from_config_llm_prompt():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rephrasers.llm:LLMQueryRephraser",
            "config": {
                "llm": {
                    "type": "ragbits.core.llms.litellm:LiteLLM",
                    "config": {"model_name": "some_model"},
                },
                "prompt": {"type": "ragbits.document_search.retrieval.rephrasers.llm:LLMQueryRephraserPrompt"},
                "default_options": {
                    "n": 4,
                },
            },
        }
    )
    rephraser: QueryRephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, LLMQueryRephraser)
    assert isinstance(rephraser._llm, LiteLLM)
    assert issubclass(rephraser._prompt, LLMQueryRephraserPrompt)
    assert rephraser.default_options.n == 4
