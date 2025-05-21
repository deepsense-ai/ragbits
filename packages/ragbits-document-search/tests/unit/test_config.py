import sys
from pathlib import Path

import pytest

from ragbits.core.config import CoreConfig
from ragbits.core.utils._pyproject import get_config_instance
from ragbits.core.utils.config_handling import NoPreferredConfigError
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search._main import DocumentSearch
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker

projects_dir = Path(__file__).parent / "testprojects"

# So that we can import the factory functions
sys.path.append(str(projects_dir))


def test_preferred_subclass_instance_yaml():
    """
    Tests that DocumentSearch.preferred_subclass uses the default yaml configuration
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instances_yaml",
    )
    instance: DocumentSearch = DocumentSearch.preferred_subclass(config)
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.reranker, NoopReranker)
    assert instance.reranker.default_options.top_n == 17
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 147


def test_preferred_subclass_instance_nested_yaml():
    """
    Tests that DocumentSearch.preferred_subclass uses the default yaml configuration
    and that configuration in the explicit `document_search` field is preferred if present
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_nested_yaml",
    )
    instance: DocumentSearch = DocumentSearch.preferred_subclass(config)
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.reranker, NoopReranker)
    assert instance.reranker.default_options.top_n == 17
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 12


def test_preferred_subclass_yaml_override():
    """
    Tests that DocumentSearch.preferred_subclass uses the given yaml configuration
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "empty_project",
    )
    instance: DocumentSearch = DocumentSearch.preferred_subclass(
        config, yaml_path_override=projects_dir / "project_with_instances_yaml" / "instances.yaml"
    )
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.reranker, NoopReranker)
    assert instance.reranker.default_options.top_n == 17
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 147


def test_preferred_subclass_instance_nested_yaml_ovverride():
    """
    Tests that DocumentSearch.preferred_subclass uses the given yaml configuration
    and that configuration in the explicit `document_search` field is preferred if present
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "empty_project",
    )
    instance: DocumentSearch = DocumentSearch.preferred_subclass(
        config, yaml_path_override=projects_dir / "project_with_nested_yaml" / "instances.yaml"
    )
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.reranker, NoopReranker)
    assert instance.reranker.default_options.top_n == 17
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 12


def test_preferred_subclass_factory():
    """
    Tests that DocumentSearch.preferred_subclass uses the default factory configuration
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instance_factory",
    )
    instance: DocumentSearch = DocumentSearch.preferred_subclass(config)
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.reranker, NoopReranker)
    assert instance.reranker.default_options.top_n == 223
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 223


def test_preferred_subclass_factory_override():
    """
    Tests that DocumentSearch.preferred_subclass uses the explicitely given factory function
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instance_factory",
    )
    instance: DocumentSearch = DocumentSearch.preferred_subclass(
        config, factory_path_override="project_with_instance_factory.factories:create_document_search_instance_825"
    )
    assert isinstance(instance, DocumentSearch)
    assert isinstance(instance.reranker, NoopReranker)
    assert instance.reranker.default_options.top_n == 825
    assert isinstance(instance.vector_store, InMemoryVectorStore)
    assert instance.vector_store.default_options.k == 825


def test_preferred_subclass_factory_no_configuration():
    """
    Tests that DocumentSearch.preferred_subclass raises NoPreferredConfigError when no configuration is available
    """
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "empty_project",
    )
    with pytest.raises(NoPreferredConfigError):
        DocumentSearch.preferred_subclass(config)
