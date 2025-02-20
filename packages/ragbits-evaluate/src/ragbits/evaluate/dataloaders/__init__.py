from ragbits.core.utils.config_handling import import_by_path
from ragbits.evaluate.config import EvaluateConfig
from ragbits.evaluate.dataloaders.base import DataLoader

__all__ = ["DataLoader"]


def get_dataloader_instance(
    config: EvaluateConfig, dataloader_args: str, dataloader_cls_override: str | None = None
) -> DataLoader:
    """
    A function for instantiation of dataloader
    Args:
        config: configuration of ragbits.evaluate module
        dataloader_args: comma separated arguments of dataloader
        dataloader_cls_override: optional path to override of default dataloader class
    Returns:
        DataLoader
    """
    dataloader_cls = dataloader_cls_override or config.dataloader_default_class
    return import_by_path(dataloader_cls)(*dataloader_args.split(","))
