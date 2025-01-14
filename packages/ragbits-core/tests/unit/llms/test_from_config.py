from ragbits.core.llms import LLM
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.utils.config_handling import ObjectContructionConfig


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.llms.litellm:LiteLLM",
            "config": {
                "model_name": "some_model",
                "use_structured_output": True,
                "default_options": {
                    "frequency_penalty": 0.2,
                    "n": 42,
                },
            },
        }
    )
    llm: LLM = LLM.subclass_from_config(config)
    assert isinstance(llm, LiteLLM)
    assert llm.model_name == "some_model"
    assert llm.use_structured_output is True
    assert isinstance(llm.default_options, LiteLLMOptions)
    assert llm.default_options.frequency_penalty == 0.2
    assert llm.default_options.n == 42


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "LiteLLM"})
    llm: LLM = LLM.subclass_from_config(config)
    assert isinstance(llm, LiteLLM)
