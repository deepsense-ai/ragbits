import sys

from ragbits.core.utils.config_handling import import_by_path

from .base import DataLoader

module = sys.modules[__name__]


def dataloader_factory(config: dict) -> DataLoader:
    """
    A function creating dataloader from a dataloder config
    Args:
        config - a dataloader configuration
    Returns:
        DataLoader
    """
    dataloader_class = import_by_path(config["type"], module)
    return dataloader_class.from_config({"config": config["options"]})
