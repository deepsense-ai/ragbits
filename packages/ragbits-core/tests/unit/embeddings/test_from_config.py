from ragbits.core.embeddings import Embedder, NoopEmbedder
from ragbits.core.embeddings.litellm import LiteLLMEmbedder, LiteLLMEmbedderOptions
from ragbits.core.embeddings.sparse import BagOfTokens, BagOfTokensOptions, SparseEmbedder
from ragbits.core.types import NOT_GIVEN
from ragbits.core.utils.config_handling import ObjectContructionConfig


def test_subclass_from_config_litellm():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.litellm:LiteLLMEmbedder",
            "config": {
                "model": "some_model",
                "default_options": {
                    "option1": "value1",
                    "option2": "value2",
                },
            },
        }
    )
    embedder: Embedder = Embedder.subclass_from_config(config)
    assert isinstance(embedder, LiteLLMEmbedder)
    assert embedder.model == "some_model"
    assert embedder.default_options == LiteLLMEmbedderOptions(
        dimensions=NOT_GIVEN,
        timeout=NOT_GIVEN,
        user=NOT_GIVEN,
        encoding_format=NOT_GIVEN,
        option1="value1",
        option2="value2",
    )  # type: ignore


def test_subclass_from_config_default_path_litellm():
    config = ObjectContructionConfig.model_validate({"type": "NoopEmbedder"})
    embedder: Embedder = Embedder.subclass_from_config(config)
    assert isinstance(embedder, NoopEmbedder)


def test_subclass_from_config_bag_of_tokens():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.sparse:BagOfTokens",
            "config": {
                "default_options": {
                    "option1": "value1",
                    "option2": "value2",
                },
            },
        }
    )
    embedder: SparseEmbedder = SparseEmbedder.subclass_from_config(config)
    assert isinstance(embedder, BagOfTokens)
    assert embedder.default_options == BagOfTokensOptions(
        model_name="gpt-4o",
        encoding_name=NOT_GIVEN,
        min_token_count=NOT_GIVEN,
        option1="value1",
        option2="value2",
    )  # type: ignore
