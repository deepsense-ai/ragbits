import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from ragbits.core.config import CoreConfig, core_config
from ragbits.core.options import Options, OptionsT
from ragbits.core.utils._pyproject import get_config_instance
from ragbits.core.utils.config_handling import (
    ConfigurableComponent,
    InvalidConfigError,
    ObjectConstructionConfig,
    WithConstructionConfig,
)

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


class ExampleBaseModel(BaseModel):
    foo: str
    bar: int


class ExampleModel:
    foo: str
    bar: int


class ExampleClassWithModelType(WithConstructionConfig):
    default_module = sys.modules[__name__]
    configuration_key = "example"
    config_model = ExampleBaseModel

    def __init__(self, foo: str, bar: int) -> None:
        self.foo = foo
        self.bar = bar


class ExampleConfigurableComponentClass(ConfigurableComponent):
    config_model = ExampleBaseModel
    options_cls = Options

    def __init__(self, foo: str, bar: int, default_options: type[OptionsT]) -> None:
        super().__init__(default_options=default_options)
        self.foo = foo
        self.bar = bar


def example_factory() -> ExampleClassWithConfigMixin:
    return ExampleSubclass("aligator", 42)


def test_default_from_config():
    config = {"foo": "foo", "bar": 1}
    with patch.object(ExampleBaseModel, "model_validate", wraps=ExampleBaseModel.model_validate) as mock_validate:
        instance = ExampleClassWithConfigMixin.from_config(config)
        assert instance.foo == "foo"
        assert instance.bar == 1
        assert instance.config_model is None
        mock_validate.assert_not_called()


def test_default_from_config_when_model_type_set():
    config = {"foo": "foo", "bar": 1}
    with patch.object(ExampleBaseModel, "model_validate", wraps=ExampleBaseModel.model_validate) as mock_validate:
        ExampleClassWithModelType.from_config(config)
        mock_validate.assert_called_once_with(config)


def test_default_from_config_with_incorrect_config():
    config = {"foo": "foo"}
    with pytest.raises(InvalidConfigError):
        ExampleClassWithModelType.from_config(config)


def test_default_from_config_with_not_base_model():
    config = {"foo": "foo", "bar": 1}
    ExampleClassWithModelType.config_model = ExampleModel  # type: ignore
    with pytest.raises(TypeError):
        ExampleClassWithModelType.from_config(config)


def test_configurable_component_from_config_with_model_type_set():
    config = {"foo": "foo", "bar": 1}
    with patch.object(ExampleBaseModel, "model_validate", wraps=ExampleBaseModel.model_validate) as mock_validate:
        ExampleConfigurableComponentClass.from_config(config)
        mock_validate.assert_called_once_with(config)


def test_configurable_component_from_config_without_model_type():
    config = {"foo": "foo", "bar": 1}
    ExampleConfigurableComponentClass.config_model = None  # type: ignore
    with patch.object(ExampleBaseModel, "model_validate", wraps=ExampleBaseModel.model_validate) as mock_validate:
        instance = ExampleConfigurableComponentClass.from_config(config)
        assert isinstance(instance, ExampleConfigurableComponentClass)
        assert instance.foo == "foo"
        assert instance.bar == 1
        assert instance.config_model is None
        mock_validate.assert_not_called()


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
