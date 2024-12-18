from ragbits.core.embeddings import Embeddings, NoopEmbeddings
from ragbits.core.embeddings.litellm import LiteLLMEmbeddings, LiteLLMEmbeddingsOptions
from ragbits.core.types import NOT_GIVEN
from ragbits.core.utils.config_handling import ObjectContructionConfig


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.litellm:LiteLLMEmbeddings",
            "config": {
                "model": "some_model",
                "default_options": {
                    "option1": "value1",
                    "option2": "value2",
                },
            },
        }
    )
    embedding: Embeddings = Embeddings.subclass_from_config(config)
    assert isinstance(embedding, LiteLLMEmbeddings)
    assert embedding.model == "some_model"
    assert embedding.default_options == LiteLLMEmbeddingsOptions(
        dimensions=NOT_GIVEN,
        timeout=NOT_GIVEN,
        user=NOT_GIVEN,
        encoding_format=NOT_GIVEN,
        option1="value1",
        option2="value2",
    )  # type: ignore


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "NoopEmbeddings"})
    embedding: Embeddings = Embeddings.subclass_from_config(config)
    assert isinstance(embedding, NoopEmbeddings)
