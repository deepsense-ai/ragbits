import sys
from pathlib import Path

import pytest

from ragbits.core.config import CoreConfig, core_config
from ragbits.core.utils._pyproject import get_config_instance
from ragbits.core.utils.config_handling import InvalidConfigError, ObjectConstructionConfig, WithConstructionConfig

projects_dir = Path(__file__).parent / "testprojects"


class ExampleClassWithConfigMixin(WithConstructionConfig):
    default_module = sys.modules[__name__]
    configuration_key = "example"

    def __init__(self, foo: str, bar: int) -> None:
        self.foo = foo
        self.bar = bar


class ExampleSubclass(ExampleClassWithConfigMixin): ...


class ExampleWithNoDefaultModule(WithConstructionConfig):
    def __init__(self, foo: str, bar: int) -> None:
        self.foo = foo
        self.bar = bar


def example_factory() -> ExampleClassWithConfigMixin:
    return ExampleSubclass("aligator", 42)


def test_default_from_config():
    config = {"foo": "foo", "bar": 1}
    instance = ExampleClassWithConfigMixin.from_config(config)
    assert instance.foo == "foo"
    assert instance.bar == 1


def test_subclass_from_config():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ExampleSubclass",
            "config": {"foo": "foo", "bar": 1},
        }
    )
    instance = ExampleClassWithConfigMixin.subclass_from_config(config)
    assert isinstance(instance, ExampleSubclass)
    assert instance.foo == "foo"
    assert instance.bar == 1


def test_incorrect_subclass_from_config():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ExampleWithNoDefaultModule",  # Not a subclass of ExampleClassWithConfigMixin
            "config": {"foo": "foo", "bar": 1},
        }
    )
    with pytest.raises(InvalidConfigError):
        ExampleClassWithConfigMixin.subclass_from_config(config)


def test_no_default_module():
    config = ObjectConstructionConfig.model_validate(
        {
            "type": "ExampleWithNoDefaultModule",
            "config": {"foo": "foo", "bar": 1},
        }
    )
    with pytest.raises(InvalidConfigError):
        ExampleWithNoDefaultModule.subclass_from_config(config)


def test_subclass_from_factory():
    instance = ExampleClassWithConfigMixin.subclass_from_factory("unit.utils.test_config_handling:example_factory")
    assert isinstance(instance, ExampleSubclass)
    assert instance.foo == "aligator"
    assert instance.bar == 42


def test_subclass_from_factory_incorrect_class():
    with pytest.raises(InvalidConfigError):
        ExampleWithNoDefaultModule.subclass_from_factory("unit.utils.test_config_handling:example_factory")


def test_preferred_subclass_factory_override():
    instance = ExampleClassWithConfigMixin.preferred_subclass(
        core_config, factory_path_override="unit.utils.test_config_handling:example_factory"
    )
    assert isinstance(instance, ExampleSubclass)
    assert instance.foo == "aligator"
    assert instance.bar == 42


def test_preferred_subclass_pyproject_factory():
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instance_factory",
    )
    instance = ExampleClassWithConfigMixin.preferred_subclass(config)
    assert isinstance(instance, ExampleSubclass)
    assert instance.foo == "aligator"
    assert instance.bar == 42


def test_preferred_subclass_instance_yaml():
    config = get_config_instance(
        CoreConfig,
        subproject="core",
        current_dir=projects_dir / "project_with_instances_yaml",
    )
    instance = ExampleClassWithConfigMixin.preferred_subclass(config)
    assert isinstance(instance, ExampleSubclass)
    assert instance.foo == "I am a foo"
    assert instance.bar == 122
