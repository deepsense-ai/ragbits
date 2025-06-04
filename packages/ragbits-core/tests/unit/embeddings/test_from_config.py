import litellm
import pytest

from ragbits.core.embeddings import DenseEmbedder, NoopEmbedder
from ragbits.core.embeddings.dense import LiteLLMEmbedder, LiteLLMEmbedderOptions
from ragbits.core.embeddings.sparse import BagOfTokens, BagOfTokensOptions, SparseEmbedder
from ragbits.core.types import NOT_GIVEN
from ragbits.core.utils.config_handling import ObjectConstructionConfig


def test_subclass_from_config_litellm():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.dense:LiteLLMEmbedder",
            "config": {
                "model_name": "some_model",
                "default_options": {
                    "option1": "value1",
                    "option2": "value2",
                },
            },
        }
    )
    embedder: DenseEmbedder = DenseEmbedder.subclass_from_config(config)
    assert isinstance(embedder, LiteLLMEmbedder)
    assert embedder.model_name == "some_model"
    assert embedder.default_options == LiteLLMEmbedderOptions(
        dimensions=NOT_GIVEN,
        timeout=NOT_GIVEN,
        user=NOT_GIVEN,
        encoding_format=NOT_GIVEN,
        option1="value1",
        option2="value2",
    )  # type: ignore


def test_subclass_from_config_default_path_litellm():
    config = ObjectConstructionConfig.model_validate({"type": "NoopEmbedder"})
    embedder: DenseEmbedder = DenseEmbedder.subclass_from_config(config)
    assert isinstance(embedder, NoopEmbedder)


def test_subclass_from_config_bag_of_tokens():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.sparse:BagOfTokens",
            "config": {
                "model_name": "gpt-4o",
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
        min_token_count=NOT_GIVEN,
        option1="value1",
        option2="value2",
    )  # type: ignore


def test_subclass_from_config_bag_of_tokens_both_specified():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ragbits.core.embeddings.sparse:BagOfTokens",
            "config": {
                "model_name": "gpt-4o",
                "encoding_name": "cl100k_base",
                "default_options": {
                    "option1": "value1",
                    "option2": "value2",
                },
            },
        }
    )
    with pytest.raises(ValueError, match="Please specify only one of encoding_name or model_name"):
        SparseEmbedder.subclass_from_config(config)


def test_from_config_with_router():
    config = ObjectConstructionConfig(
        type="ragbits.core.embeddings.dense:LiteLLMEmbedder",
        config={
            "model_name": "text-embedding-3-small",
            "api_key": "test_api_key",
            "router": [
                {
                    "model_name": "small",
                    "litellm_params": {
                        "model": "text-embedding-3-small",
                        "dimensions": 3000,
                        "api_key": "test_api_key",
                    },
                },
                {
                    "model_name": "large",
                    "litellm_params": {
                        "model": "text-embedding-3-large",
                        "api_key": "test_api_key",
                    },
                },
            ],
        },
    )

    embedder: DenseEmbedder = DenseEmbedder.subclass_from_config(config)
    assert isinstance(embedder, LiteLLMEmbedder)
    assert embedder.api_base is None
    assert embedder.model_name == "text-embedding-3-small"
    assert embedder.api_key == "test_api_key"
    assert isinstance(embedder.router, litellm.router.Router)
    assert len(embedder.router.model_list) == 2
    assert embedder.router.model_list[0]["model_name"] == "small"
    assert embedder.router.model_list[0]["litellm_params"]["dimensions"] == 3000
    assert embedder.router.model_list[1]["model_name"] == "large"
    assert embedder.router.model_list[1]["litellm_params"]["model"] == "text-embedding-3-large"
