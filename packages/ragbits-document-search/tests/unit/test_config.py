import sys
from pathlib import Path

import pytest

from ragbits.core.config import CoreConfig
from ragbits.core.embeddings.noop import NoopEmbeddings
from ragbits.core.utils._pyproject import get_config_instance
from ragbits.core.utils.config_handling import NoDefaultConfigError
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search._main import DocumentSearch
from ragbits.document_search.processing_strategy import SequentialProcessing
from ragbits.document_search.query_rephraser import NoopQueryRephraser
from ragbits.document_search.reranker import NoopReranker

projects_dir = Path(__file__).parent / "testprojects"

# So that we can import the factory functions
sys.path.append(str(projects_dir))


def test_subclass_from_defaults_instance_yaml():
    """
    Tests that DocumentSearch.subclass_from_defaults uses the default yaml configuration
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instances_yaml",
    )
    instance = DocumentSearch.subclass_from_defaults(config)
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.embedder, NoopEmbeddings)
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 147


def test_subclass_from_defaults_instance_nested_yaml():
    """
    Tests that DocumentSearch.subclass_from_defaults uses the default yaml configuration
    and that configuration in the explicit `document_search` field is preferred if present
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_nested_yaml",
    )
    instance = DocumentSearch.subclass_from_defaults(config)
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.embedder, NoopEmbeddings)
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 12


def test_subclass_from_defaults_yaml_override():
    """
    Tests that DocumentSearch.subclass_from_defaults uses the given yaml configuration
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "empty_project",
    )
    instance = DocumentSearch.subclass_from_defaults(
        config, yaml_path_override=projects_dir / "project_with_instances_yaml" / "instances.yaml"
    )
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.embedder, NoopEmbeddings)
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 147


def test_subclass_from_defaults_instance_nested_yaml_ovverride():
    """
    Tests that DocumentSearch.subclass_from_defaults uses the given yaml configuration
    and that configuration in the explicit `document_search` field is preferred if present
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "empty_project",
    )
    instance = DocumentSearch.subclass_from_defaults(
        config, yaml_path_override=projects_dir / "project_with_nested_yaml" / "instances.yaml"
    )
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.embedder, NoopEmbeddings)
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 12


def test_subclass_from_defaults_factory():
    """
    Tests that DocumentSearch.subclass_from_defaults uses the default factory configuration
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instance_factory",
    )
    instance = DocumentSearch.subclass_from_defaults(config)
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.embedder, NoopEmbeddings)
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 223


def test_subclass_from_defaults_factory_override():
    """
    Tests that DocumentSearch.subclass_from_defaults uses the explicitely given factory function
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instance_factory",
    )
    instance = DocumentSearch.subclass_from_defaults(
        config, factory_path_override="project_with_instance_factory.factories:create_document_search_instance_825"
    )
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.embedder, NoopEmbeddings)
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 825


def test_subclass_from_defaults_factory_no_configuration():
    """
    Tests that DocumentSearch.subclass_from_defaults raises NoDefaultConfigError when no configuration is available
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "empty_project",
    )
    with pytest.raises(NoDefaultConfigError):
        DocumentSearch.subclass_from_defaults(config)


@pytest.mark.asyncio
async def test_from_config_with_minimal_config() -> None:
    """Test creating a DocumentSearch instance from a minimal config."""
    config = {
        "vector_store": {
            "type": "InMemoryVectorStore",
            "config": {
                "default_embedder": {
                    "type": "DummyEmbeddings",
                    "config": {},
                },
            },
        },
    }

    document_search = await DocumentSearch.from_config(config)

    assert isinstance(document_search.vector_store, InMemoryVectorStore)
    assert isinstance(document_search.query_rephraser, NoopQueryRephraser)
    assert isinstance(document_search.reranker, NoopReranker)
    assert isinstance(document_search.processing_strategy, SequentialProcessing)


@pytest.mark.asyncio
async def test_from_config_with_full_config() -> None:
    """Test creating a DocumentSearch instance from a full config."""
    config = {
        "vector_store": {
            "type": "InMemoryVectorStore",
            "config": {
                "default_embedder": {
                    "type": "DummyEmbeddings",
                    "config": {},
                },
            },
        },
        "rephraser": {"type": "NoopQueryRephraser"},
        "reranker": {"type": "NoopReranker"},
        "processing_strategy": {"type": "SequentialProcessing"},
    }

    document_search = await DocumentSearch.from_config(config)

    assert isinstance(document_search.vector_store, InMemoryVectorStore)
    assert isinstance(document_search.query_rephraser, NoopQueryRephraser)
    assert isinstance(document_search.reranker, NoopReranker)
    assert isinstance(document_search.processing_strategy, SequentialProcessing)
