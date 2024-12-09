import sys

import pytest

from ragbits.core.utils.config_handling import InvalidConfigError, ObjectContructionConfig, WithConstructionConfig


class ExampleClassWithConfigMixin(WithConstructionConfig):
    default_module = sys.modules[__name__]

    def __init__(self, foo: str, bar: int) -> None:
        self.foo = foo
        self.bar = bar


class ExampleSubclass(ExampleClassWithConfigMixin): ...


class ExampleWithNoDefaultModule(WithConstructionConfig):
    def __init__(self, foo: str, bar: int) -> None:
        self.foo = foo
        self.bar = bar


def test_defacult_from_config():
    config = {"foo": "foo", "bar": 1}
    instance = ExampleClassWithConfigMixin.from_config(config)
    assert instance.foo == "foo"
    assert instance.bar == 1


def test_subclass_from_config():
    config = ObjectContructionConfig.model_validate(
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
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ExampleWithNoDefaultModule",  # Not a subclass of ExampleClassWithConfigMixin
            "config": {"foo": "foo", "bar": 1},
        }
    )
    with pytest.raises(InvalidConfigError):
        ExampleClassWithConfigMixin.subclass_from_config(config)


def test_no_default_module():
    config = ObjectContructionConfig.model_validate(
        {
            "type": "ExampleWithNoDefaultModule",
            "config": {"foo": "foo", "bar": 1},
        }
    )
    with pytest.raises(InvalidConfigError):
        ExampleWithNoDefaultModule.subclass_from_config(config)
