import sys

from omegaconf import DictConfig

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import DataLoader

__all__ = [DataLoader]

module = sys.modules[__name__]


def dataloader_factory(config: DictConfig) -> DataLoader:
    dataloader_class = get_cls_from_config(config.type, module)
    return dataloader_class(config.options)
