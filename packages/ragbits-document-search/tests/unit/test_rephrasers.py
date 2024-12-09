from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.llm import LLMQueryRephraser
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompts import QueryRephraserPrompt


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {"type": "ragbits.document_search.retrieval.rephrasers:NoopQueryRephraser"}
    )
    rephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, NoopQueryRephraser)


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "NoopQueryRephraser"})
    rephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, NoopQueryRephraser)


def test_subclass_from_config_llm():
    config = ObjectContructionConfig.model_validate(
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
    rephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, LLMQueryRephraser)
    assert isinstance(rephraser._llm, LiteLLM)
    assert rephraser._llm.model_name == "some_model"


def test_subclass_from_config_llm_prompt():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.document_search.retrieval.rephrasers.llm:LLMQueryRephraser",
            "config": {
                "llm": {
                    "type": "ragbits.core.llms.litellm:LiteLLM",
                    "config": {"model_name": "some_model"},
                },
                "prompt": {"type": "QueryRephraserPrompt"},
            },
        }
    )
    rephraser = QueryRephraser.subclass_from_config(config)
    assert isinstance(rephraser, LLMQueryRephraser)
    assert isinstance(rephraser._llm, LiteLLM)
    assert issubclass(rephraser._prompt, QueryRephraserPrompt)
