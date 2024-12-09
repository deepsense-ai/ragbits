from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.metadata_stores.in_memory import InMemoryMetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ragbits.core.metadata_stores:InMemoryMetadataStore",
        }
    )
    store = MetadataStore.subclass_from_config(config)
    assert isinstance(store, InMemoryMetadataStore)


def test_subclass_from_config_default_path():
    config = ObjectContructionConfig.model_validate({"type": "InMemoryMetadataStore"})
    store = MetadataStore.subclass_from_config(config)
    assert isinstance(store, InMemoryMetadataStore)
