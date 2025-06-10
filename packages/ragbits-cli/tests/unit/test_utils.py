import sys

from ragbits.cli._utils import get_instance_or_exit
from ragbits.core.utils.config_handling import WithConstructionConfig


class ExampleClassForCLI(WithConstructionConfig):
    default_module = sys.modules[__name__]
    configuration_key = "example_cli"

    def __init__(self, foo: str, bar: int) -> None:
        self.foo = foo
        self.bar = bar


def sync_factory_for_cli() -> ExampleClassForCLI:
    return ExampleClassForCLI("sync_cli", 123)


async def async_factory_for_cli() -> ExampleClassForCLI:
    """Async factory function for testing CLI with async support."""
    return ExampleClassForCLI("async_cli", 456)


def test_get_instance_or_exit_with_sync_factory():
    """Test that get_instance_or_exit works with sync factory functions."""
    instance = get_instance_or_exit(ExampleClassForCLI, factory_path="sync_factory_for_cli")
    assert isinstance(instance, ExampleClassForCLI)
    assert instance.foo == "sync_cli"
    assert instance.bar == 123


def test_get_instance_or_exit_with_async_factory():
    """Test that get_instance_or_exit works with async factory functions."""
    instance = get_instance_or_exit(ExampleClassForCLI, factory_path="async_factory_for_cli")
    assert isinstance(instance, ExampleClassForCLI)
    assert instance.foo == "async_cli"
    assert instance.bar == 456
