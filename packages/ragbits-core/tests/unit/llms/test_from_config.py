import litellm

from ragbits.core.llms import LLM
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.utils.config_handling import ObjectConstructionConfig


def test_subclass_from_config():
    config = ObjectConstructionConfig.model_validate(
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
    config = ObjectConstructionConfig.model_validate({"type": "LiteLLM"})
    llm: LLM = LLM.subclass_from_config(config)
    assert isinstance(llm, LiteLLM)


def test_from_config_with_router():
    config = ObjectConstructionConfig(
        type="ragbits.core.llms.litellm:LiteLLM",
        config={
            "model_name": "gpt-4-turbo",
            "api_key": "test_api_key",
            "router": [
                {
                    "model_name": "gpt-4o",
                    "litellm_params": {
                        "model": "azure/gpt-4o-eval-1",
                        "api_key": "test_api_key",
                        "api_version": "2024-07-19-test",
                        "api_base": "https://test-api.openai.azure.com",
                    },
                },
                {
                    "model_name": "gpt-4o",
                    "litellm_params": {
                        "model": "azure/gpt-4o-eval-2",
                        "api_key": "test_api_key",
                        "api_version": "2024-07-19-test",
                        "api_base": "https://test-api.openai.azure.com",
                    },
                },
            ],
        },
    )

    llm: LLM = LLM.subclass_from_config(config)
    assert isinstance(llm, LiteLLM)
    assert llm.api_base is None
    assert llm.model_name == "gpt-4-turbo"
    assert llm.api_key == "test_api_key"
    assert isinstance(llm.router, litellm.router.Router)
    assert len(llm.router.model_list) == 2
    assert llm.router.model_list[0]["model_name"] == "gpt-4o"
