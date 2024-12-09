from ragbits.core.embeddings import Embeddings, NoopEmbeddings
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.utils.config_handling import ObjectContructionConfig


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.litellm:LiteLLMEmbeddings",
            "config": {
                "model": "some_model",
                "options": {
                    "option1": "value1",
                    "option2": "value2",
                },
            },
        }
    )
    embedding = Embeddings.subclass_from_config(config)
    assert isinstance(embedding, LiteLLMEmbeddings)
    assert embedding.model == "some_model"
    assert embedding.options == {"option1": "value1", "option2": "value2"}


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "NoopEmbeddings"})
    embedding = Embeddings.subclass_from_config(config)
    assert isinstance(embedding, NoopEmbeddings)
